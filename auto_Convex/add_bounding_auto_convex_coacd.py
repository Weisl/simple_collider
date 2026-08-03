import os
import re
import time

import bmesh
import bpy
from bpy.types import Operator

from ..bmesh_operations.mesh_edit import bmesh_join
from ..collider_shapes.add_bounding_primitive import OBJECT_OT_add_bounding_object, _remove_draw_handle

# How often the CoACD subprocess is polled for completion while it's
# running. Polling (rather than Popen.wait()) is what keeps Blender's UI
# thread responsive - CoACD's own MCTS search can take anywhere from
# fractions of a second to many minutes depending on mesh complexity, and
# there's no way to know in advance which it'll be (#660). This also drives
# how often the status overlay redraws (draw_async_job_overlay()'s scrolling
# stripes) - process.poll() and draining the (usually empty) progress queue
# are both cheap, so this runs at a plain 60fps redraw cadence for smooth
# animation rather than the coarser interval a "just check if it's done yet"
# poll alone would need.
COACD_POLL_INTERVAL_SECONDS = 1 / 60

# CoACD already prints its own progress to stdout - section headers like
# " - Decomposition (MCTS)" and per-candidate "Processing [62.3%]" lines -
# it just wasn't being read (the subprocess inherited the console instead
# of being piped). Parsed by _parse_progress_line() (see
# OBJECT_OT_add_bounding_object._drain_async_progress()) into a short status
# string, so a multi-minute run reads as "working" instead of a silent
# elapsed-time counter that's indistinguishable from being stuck.
_COACD_PHASE_RE = re.compile(r'\[info\]\s+-\s+(.+?)\s*$')
_COACD_PCT_RE = re.compile(r'Processing \[([\d.]+)%\]')

# True while any COACD_OT_convex_decomposition instance has a job in flight.
# Module-level (not per-instance) because invoke() creates a brand new
# instance every time the operator is triggered - an instance attribute
# can't stop a *second*, independent invocation from starting. Before the
# CLI was made async (#660), a synchronously-frozen UI was an accidental
# guard against exactly this: the user physically couldn't trigger the
# operator a second time while the first call was still blocking. Now that
# Blender stays responsive during a run, nothing else prevents overlapping
# invocations - which would race on the same parent-name-derived temp
# filenames (see _job_file_prefix()) and corrupt each other's output.
_coacd_run_in_progress = False


class COACD_OT_convex_decomposition(OBJECT_OT_add_bounding_object, Operator):
    bl_idname = 'collision.coacd'
    bl_label = 'Auto Convex (High Precision)'
    bl_description = ('Create multiple convex hull colliders using CoACD (Collision-Aware Concavity and tree '
                      'search). Produces fewer, tighter-fitting hulls than V-HACD by searching for better cuts, '
                      'but is significantly slower - can take minutes on complex or non-manifold meshes')
    bl_options = {'REGISTER', 'PRESET', 'UNDO'}

    @staticmethod
    def overwrite_executable_path(path):
        """Users can overwrite the default executable path."""
        executable_path = bpy.path.abspath(path)
        return executable_path if os.path.isfile(executable_path) else False

    @staticmethod
    def set_temp_data_path(path):
        """Set folder to temporarily store the exported data."""
        if not path or not os.path.isdir(os.path.normpath(bpy.path.abspath(path))):
            import tempfile
            fallback_path = tempfile.gettempdir()
            print(f"Warning: Path is invalid or not set. Falling back to: {fallback_path}")
            return fallback_path

        data_path = os.path.normpath(bpy.path.abspath(path))
        if os.path.isdir(data_path) and os.access(data_path, os.W_OK):
            return data_path
        else:
            import tempfile
            fallback_path = tempfile.gettempdir()
            print(f"Warning: Path '{data_path}' is not writable. Falling back to: {fallback_path}")
            return fallback_path

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_decimation = True
        self.use_geo_nodes_hull = True
        self.use_modifier_stack = True
        self.use_recenter_origin = True
        self.shape = 'convex_shape'

        # Async CoACD job state (#660: CoACD ran synchronously via
        # subprocess.wait(), which froze Blender's main thread completely -
        # with no progress feedback and no way to cancel - for as long as
        # the CLI took, which for non-trivial/non-manifold real-world meshes
        # can be many minutes even with default settings. See
        # _start_next_coacd_job()/_poll_coacd_process() below: the CLI is
        # now driven from bpy.app.timers, one polled step at a time, the
        # same pattern already used for the debounce timers above.
        #
        # _async_process/_async_start_time are the generic names the shared
        # status overlay (draw_async_job_overlay() in add_bounding_primitive)
        # looks for via getattr() - VHACD_OT_convex_decomposition uses the
        # same names so both backends drive the same overlay.
        self._async_process = None
        self._async_start_time = 0.0
        self._async_job_label = 'CoACD'
        # CoACD's MCTS search is much slower than V-HACD on non-trivial
        # meshes - shown on the overlay (draw_async_job_overlay()) so a
        # multi-minute run doesn't read as hung.
        self._async_hint_text = 'This can take a few minutes for complex meshes'
        self._coacd_exe = None
        self._coacd_data_path = None
        self._coacd_pending_jobs = []
        self._coacd_results = []
        self._coacd_stage = None  # 'decompose' | 'decimate'
        self._coacd_job_ctx = None
        self._coacd_decimate_ctx = None
        self._coacd_hull_queue = []
        self._coacd_decimated_hulls = []
        self._coacd_hull_index = 0
        self._status_area = None
        self._coacd_run_id = None

        # Live progress, parsed from the running subprocess's stdout via
        # _parse_progress_line() (see OBJECT_OT_add_bounding_object -
        # _launch_async_process()/_drain_async_progress()) and the module
        # docstring on _COACD_PHASE_RE above.
        self._coacd_progress_phase = ''
        self._coacd_progress_pct = ''

        # bpy.app.timers callbacks (see _poll_coacd_process()) have no
        # guaranteed context - bpy.context.space_data is None (or belongs to
        # whatever editor the mouse happens to be over) unless the pointer
        # is currently over this operator's own VIEW_3D, which is unlikely
        # once a run takes minutes and the user's mouse wanders off. Capture
        # a stable window/area/region here at invoke time and override into
        # it for every downstream async step, rather than trusting ambient
        # bpy.context (whose space_data being None crashed
        # set_viewport_drawing() mid-way through postprocess_colliders()'s
        # per-hull loop, silently leaving every hull after the crash point
        # untransformed and unparented).
        self._invoke_window = None
        self._invoke_area = None
        self._invoke_region = None

    def invoke(self, context, event):
        if _coacd_run_in_progress:
            self.report({'ERROR'}, 'Auto Convex (High Precision) is already running - wait for it to finish, or '
                                    'select it and press Escape to cancel, before starting another run')
            return {'CANCELLED'}
        return super().invoke(context, event)

    def modal(self, context, event):
        if self._async_process is not None:
            # A CoACD job is in flight: swallow all input except viewport
            # navigation (still allowed so the user isn't locked out of
            # looking around while it runs) and cancel. Everything else -
            # including LEFTMOUSE/RET confirm - is intentionally ignored,
            # since the colliders this operator would finalize don't exist
            # yet.
            if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
                return {'PASS_THROUGH'}
            if event.type in {'RIGHTMOUSE', 'ESC'}:
                self._cancel_coacd_job(context)
                self.cancel_cleanup(context)
                return {'CANCELLED'}
            return {'RUNNING_MODAL'}

        status = super().modal(context, event)
        if status == {'FINISHED'}:
            return {'FINISHED'}
        if status == {'CANCELLED'}:
            return {'CANCELLED'}
        if status == {'PASS_THROUGH'}:
            return {'PASS_THROUGH'}
        if self.numeric_input_active:
            # direct numeric text entry (issue #640) is in progress; don't
            # let this shape's own hotkeys fire until it's confirmed/cancelled
            return status

        if event.type == 'P' and event.value == 'RELEASE':
            self.my_use_modifier_stack = not self.my_use_modifier_stack
            self.execute(context)

        return {'RUNNING_MODAL'}

    def cancel(self, context):
        self._cancel_coacd_job(context)
        context.space_data.shading.color_type = self.color_type
        _remove_draw_handle(self._handle)
        return {'CANCELLED'}

    def validate_paths_and_settings(self, context):
        """Validate executable and data paths, and report errors if invalid."""
        overwrite_path = self.overwrite_executable_path(self.prefs.coacd_executable_path)
        coacd_exe = self.prefs.coacd_default_executable_path if not overwrite_path else overwrite_path
        data_path = self.set_temp_data_path(self.prefs.data_path)
        print(f"Using data path: {data_path}")

        if not coacd_exe:
            self.report({'ERROR'},
                        'CoACD executable is required for Auto Convex (High Precision) to work. Please follow '
                        'the installation instructions and try it again')
            return None, None
        if not data_path:
            self.report({'ERROR'}, 'Invalid temporary data path')
            return None, None

        return coacd_exe, data_path

    def preprocess_objects_and_collect_data(self, context):
        """Preprocess selected objects and collect mesh data for convex decomposition."""
        collider_data = []
        meshes = []
        matrices = []

        objs = self.get_pre_processed_mesh_objs(context, default_world_spc=True)

        for base_ob, obj in objs:
            context.view_layer.objects.active = obj

            if self.obj_mode == "EDIT" and base_ob.type == 'MESH' and self.active_obj.type == 'MESH' and not self.use_loose_mesh:
                new_mesh = self.get_mesh_Edit(obj, use_modifiers=self.my_use_modifier_stack)
            else:
                new_mesh = self.mesh_from_selection(obj, use_modifiers=self.my_use_modifier_stack)

            if new_mesh is None:
                continue

            creation_mode = self.creation_mode[self.creation_mode_idx] if self.obj_mode == 'OBJECT' else \
                self.creation_mode_edit[self.creation_mode_idx]
            if creation_mode in ['INDIVIDUAL'] or self.use_loose_mesh:
                convex_collision_data = {'parent': base_ob, 'mtx_world': base_ob.matrix_world.copy(), 'mesh': new_mesh}
                collider_data.append(convex_collision_data)
            else:
                meshes.append(new_mesh)
                matrices.append(obj.matrix_world)

        if self.creation_mode[self.creation_mode_idx] == 'SELECTION':
            convex_collision_data = {'parent': self.active_obj, 'mtx_world': self.active_obj.matrix_world.copy()}
            bmeshes = [bmesh.new() for mesh in meshes]
            for bm, mesh in zip(bmeshes, meshes):
                bm.from_mesh(mesh)
            joined_mesh = bmesh_join(bmeshes, matrices)
            convex_collision_data['mesh'] = joined_mesh
            collider_data = [convex_collision_data]

        bpy.ops.object.mode_set(mode='OBJECT')
        return collider_data

    def export_mesh_for_coacd(self, context, parent, mesh, data_path):
        """Export the mesh to OBJ format for CoACD processing."""
        joined_obj = bpy.data.objects.new('debug_joined_mesh', mesh.copy())
        context.scene.collection.objects.link(joined_obj)

        # _coacd_run_id makes this filename unique per run (see execute()):
        # belt-and-suspenders against the _coacd_run_in_progress guard above
        # missing some edge case and two runs sharing the same data_path
        # ever overlapping - without it, two runs on a similarly-named
        # object would silently clobber each other's export/output files.
        filename = ''.join(c for c in parent.name if c.isalnum() or c in (' ', '.', '_')).rstrip()
        obj_filename = os.path.join(data_path, f'{filename}_{self._coacd_run_id}.obj')

        print(f'\nExporting mesh for CoACD: {obj_filename}...')

        joined_obj.select_set(True)

        bpy.ops.wm.obj_export(filepath=obj_filename, check_existing=False, export_selected_objects=True,
                              export_materials=False, export_uv=False, export_normals=False,
                              forward_axis='Y', up_axis='Z')

        bpy.data.objects.remove(joined_obj)

        return obj_filename

    def _parse_progress_line(self, line):
        """Override of the base class hook (see _drain_async_progress()):
        CoACD's stdout format - see _COACD_PHASE_RE / _COACD_PCT_RE above."""
        m = _COACD_PHASE_RE.search(line)
        if m:
            self._coacd_progress_phase = m.group(1).strip()
            self._coacd_progress_pct = ''  # new phase - stale % no longer applies
            return self._coacd_progress_phase
        m = _COACD_PCT_RE.search(line)
        if m:
            self._coacd_progress_pct = f'{m.group(1)}%'
            parts = [p for p in (self._coacd_progress_phase, self._coacd_progress_pct) if p]
            return ' '.join(parts)
        return None

    def _start_next_coacd_job(self, context):
        """Pop the next collider off the queue and launch CoACD on it
        without blocking. If the queue is empty, the whole run is done."""
        if not self._coacd_pending_jobs:
            self._finish_coacd_run(context)
            return

        convex_collision_data = self._coacd_pending_jobs.pop(0)
        parent = convex_collision_data['parent']
        mesh = convex_collision_data['mesh']
        mtx_world = convex_collision_data['mtx_world']

        obj_filename = self.export_mesh_for_coacd(context, parent, mesh, self._coacd_data_path)

        col_settings = context.scene.simple_collider
        prefs = self.prefs

        basename = os.path.splitext(os.path.basename(obj_filename))[0]
        output_filename = os.path.join(self._coacd_data_path, f'{basename}_coacd.obj')
        remesh_filename = os.path.join(self._coacd_data_path, f'{basename}_coacd_remesh.obj')

        cmd = [
            self._coacd_exe, '-i', obj_filename, '-o', output_filename, '-ro', remesh_filename,
            '-t', str(col_settings.coacd_threshold), '-c', str(col_settings.coacd_maxConvexHulls),
            '-pm', prefs.coacd_preprocessMode, '-pr', str(prefs.coacd_prepResolution),
            '-mi', str(prefs.coacd_mctsIterations), '-md', str(prefs.coacd_mctsDepth),
            '-mn', str(prefs.coacd_mctsNodes), '-r', str(prefs.coacd_resolution),
        ]

        # -d/-dt is intentionally never combined with manifold preprocessing here: the CoACD 1.0.11
        # CLI silently produces an empty output when both are active on the same pass (preprocess
        # collapses to 0 points). Hull vertex limiting is instead applied afterwards, per-hull, via
        # the decimate stage below, where -pm off is safe because each hull is already convex/manifold.
        if prefs.coacd_noMerge:
            cmd.append('-nm')
        if prefs.coacd_pca:
            cmd.append('--pca')

        print('Running CoACD...\n{}\n'.format(' '.join(cmd)))
        print(f"Using data path for CoACD: {self._coacd_data_path}")

        # No shell=True: CoACD is launched directly (not via an intermediate
        # cmd.exe/sh -c) so that killing this Popen on cancel actually kills
        # the CoACD process itself rather than leaving it running detached.
        process = self._launch_async_process(cmd, self._coacd_data_path)

        self._async_process = process
        self._coacd_stage = 'decompose'
        self._coacd_job_ctx = {
            'parent': parent,
            'mesh': mesh,
            'mtx_world': mtx_world,
            'output_filename': output_filename,
        }
        self._async_start_time = time.time()
        bpy.app.timers.register(self._poll_coacd_process, first_interval=COACD_POLL_INTERVAL_SECONDS)

    def _poll_coacd_process(self):
        """bpy.app.timers callback: check whether the current CoACD/decimate
        subprocess has finished, without blocking Blender's main thread.
        Re-arms itself via its return value for as long as the process is
        still running."""
        global _coacd_run_in_progress
        try:
            process = self._async_process
            if process is None:
                return None

            if process.poll() is None:
                self._drain_async_progress()
                if self._status_area is not None:
                    self._status_area.tag_redraw()
                return COACD_POLL_INTERVAL_SECONDS

            self._async_process = None

            # bpy.context here has no guaranteed space_data - it reflects
            # whatever the mouse happens to be over (or nothing) at the
            # moment this timer fires, not this operator's own viewport.
            # postprocess_colliders() -> primitive_postprocessing() needs a
            # real VIEW_3D context (context.space_data.shading), so override
            # into the window/area/region captured back in execute() rather
            # than trusting ambient context.
            with bpy.context.temp_override(window=self._invoke_window, area=self._invoke_area,
                                           region=self._invoke_region):
                context = bpy.context
                if self._coacd_stage == 'decompose':
                    self._handle_decompose_finished(context)
                else:
                    self._handle_decimate_finished(context)
        except ReferenceError:
            # operator has already finished/cancelled and its RNA was freed
            _coacd_run_in_progress = False
        except Exception:
            # Whatever went wrong, never leave the module-level run lock
            # stuck - that would permanently block every future Auto Convex
            # (High Precision) invocation until Blender restarts. Still
            # re-raised so the actual error is printed to the console as
            # usual.
            _coacd_run_in_progress = False
            raise
        return None

    def import_decomposed_meshes(self, obj_path):
        """Import the decomposed meshes from the CoACD output OBJ file."""
        imported = []

        bpy.ops.wm.obj_import(filepath=obj_path, forward_axis='Y', up_axis='Z')
        imported.extend(bpy.context.selected_objects)

        for ob in imported:
            ob.select_set(False)

        return imported

    def _handle_decompose_finished(self, context):
        """Called once the main decomposition subprocess for one collider
        has exited. Imports the result (if any) and either kicks off the
        per-hull decimate pass or finalizes this collider's job."""
        job = self._coacd_job_ctx
        output_filename = job['output_filename']
        parent = job['parent']
        mesh = job['mesh']
        mtx_world = job['mtx_world']

        if not os.path.isfile(output_filename) or os.path.getsize(output_filename) == 0:
            self.report({'WARNING'}, f'CoACD failed to generate colliders for {parent.name}')
            bpy.data.meshes.remove(mesh)
            self._coacd_job_ctx = None
            self._start_next_coacd_job(context)
            return

        imported = self.import_decomposed_meshes(output_filename)

        if context.scene.simple_collider.coacd_decimate:
            self._coacd_hull_queue = list(imported)
            self._coacd_decimated_hulls = []
            self._coacd_hull_index = 0
            self._start_next_decimate_hull(context)
        else:
            self._coacd_results.append({'colliders': imported, 'parent': parent, 'mtx_world': mtx_world})
            bpy.data.meshes.remove(mesh)
            self._coacd_job_ctx = None
            self._start_next_coacd_job(context)

    def _start_next_decimate_hull(self, context):
        """Limit the vertex count of each convex hull individually, one hull
        at a time, without blocking. CoACD's own -d/-dt decimation is run
        here as a second, per-hull pass instead of alongside the main
        decomposition: feeding it a fresh manifold single-hull mesh with
        preprocessing forced off avoids the empty-output bug noted in
        _start_next_coacd_job(), and (unlike feeding it the combined
        multi-hull file) doesn't crash the CLI."""
        if not self._coacd_hull_queue:
            job = self._coacd_job_ctx
            self._coacd_results.append({
                'colliders': self._coacd_decimated_hulls,
                'parent': job['parent'],
                'mtx_world': job['mtx_world'],
            })
            bpy.data.meshes.remove(job['mesh'])
            self._coacd_job_ctx = None
            self._coacd_decimated_hulls = []
            self._start_next_coacd_job(context)
            return

        col_settings = context.scene.simple_collider
        hull_obj = self._coacd_hull_queue.pop(0)

        for ob in context.selected_objects:
            ob.select_set(False)
        hull_obj.select_set(True)
        context.view_layer.objects.active = hull_obj

        i = self._coacd_hull_index
        self._coacd_hull_index += 1

        basename = ''.join(c for c in hull_obj.name if c.isalnum() or c in (' ', '.', '_')).rstrip()
        hull_filename = os.path.join(self._coacd_data_path, f'{basename}_{self._coacd_run_id}_hull_{i}.obj')
        decimated_filename = os.path.join(self._coacd_data_path, f'{basename}_{self._coacd_run_id}_hull_{i}_dec.obj')
        remesh_filename = os.path.join(self._coacd_data_path,
                                       f'{basename}_{self._coacd_run_id}_hull_{i}_dec_remesh.obj')

        bpy.ops.wm.obj_export(filepath=hull_filename, check_existing=False, export_selected_objects=True,
                              export_materials=False, export_uv=False, export_normals=False,
                              forward_axis='Y', up_axis='Z')

        cmd = [
            self._coacd_exe, '-i', hull_filename, '-o', decimated_filename, '-ro', remesh_filename,
            '-t', str(col_settings.coacd_threshold), '-c', '-1', '-pm', 'off',
            '-d', '-dt', str(col_settings.coacd_maxHullVertCount),
        ]
        process = self._launch_async_process(cmd, self._coacd_data_path)

        hull_obj.select_set(False)

        self._async_process = process
        self._coacd_stage = 'decimate'
        self._coacd_decimate_ctx = {
            'hull_obj': hull_obj,
            'hull_filename': hull_filename,
            'decimated_filename': decimated_filename,
            'remesh_filename': remesh_filename,
        }
        self._async_start_time = time.time()
        bpy.app.timers.register(self._poll_coacd_process, first_interval=COACD_POLL_INTERVAL_SECONDS)

    def _handle_decimate_finished(self, context):
        """Called once a single hull's decimate subprocess has exited."""
        d = self._coacd_decimate_ctx
        hull_obj = d['hull_obj']
        hull_filename = d['hull_filename']
        decimated_filename = d['decimated_filename']
        remesh_filename = d['remesh_filename']

        if os.path.isfile(decimated_filename) and os.path.getsize(decimated_filename) > 0:
            bpy.data.objects.remove(hull_obj)
            bpy.ops.wm.obj_import(filepath=decimated_filename, forward_axis='Y', up_axis='Z')
            new_hulls = context.selected_objects[:]
            for ob in new_hulls:
                ob.select_set(False)
            self._coacd_decimated_hulls.extend(new_hulls)
        else:
            self.report({'WARNING'}, f'CoACD hull decimation failed for {hull_obj.name}, keeping original hull')
            self._coacd_decimated_hulls.append(hull_obj)

        for f in (hull_filename, decimated_filename, remesh_filename):
            if os.path.isfile(f):
                os.remove(f)

        self._coacd_decimate_ctx = None
        self._start_next_decimate_hull(context)

    def _cancel_coacd_job(self, context):
        """Kill any in-flight CoACD subprocess and drop all queued/partial
        state for the current run. Called from modal()'s ESC/RIGHTMOUSE
        handling and from cancel()."""
        global _coacd_run_in_progress
        _coacd_run_in_progress = False

        if self._async_process is not None:
            try:
                self._async_process.kill()
                self._async_process.wait(timeout=5)
            except Exception:
                pass
            self._async_process = None

        if self._coacd_job_ctx is not None:
            mesh = self._coacd_job_ctx.get('mesh')
            if mesh is not None:
                try:
                    bpy.data.meshes.remove(mesh)
                except ReferenceError:
                    pass
            self._coacd_job_ctx = None

        if self._coacd_decimate_ctx is not None:
            hull_obj = self._coacd_decimate_ctx.get('hull_obj')
            if hull_obj is not None:
                self.remove_objects([hull_obj])
            self._coacd_decimate_ctx = None

        self.remove_objects(self._coacd_hull_queue)
        self.remove_objects(self._coacd_decimated_hulls)
        for result in self._coacd_results:
            self.remove_objects(result['colliders'])

        self._coacd_pending_jobs = []
        self._coacd_results = []
        self._coacd_hull_queue = []
        self._coacd_decimated_hulls = []
        self._coacd_stage = None

    def postprocess_colliders(self, context, convex_decomposition_data):
        """Postprocess the imported colliders: naming, parenting, and final setup."""
        context.view_layer.objects.active = self.active_obj

        for convex_collisions_data in convex_decomposition_data:
            convex_collision = convex_collisions_data['colliders']
            parent = convex_collisions_data['parent']
            mtx_world = convex_collisions_data['mtx_world']

            for new_collider in convex_collision:
                new_collider.name = super().collider_name(basename=parent.name)

                if self.creation_mode[self.creation_mode_idx] == 'INDIVIDUAL':
                    if not self.use_loose_mesh:
                        new_collider.matrix_world = mtx_world
                    self.apply_transform(new_collider, rotation=True, scale=True)

                self.custom_set_parent(context, parent, new_collider)
                collections = parent.users_collection
                self.primitive_postprocessing(context, new_collider, collections)
                self.new_colliders_list.append(new_collider)

    def _finish_coacd_run(self, context):
        """Called once every queued collider has been decomposed (and
        decimated, if enabled). Mirrors what the old synchronous execute()
        did after its blocking loop finished."""
        global _coacd_run_in_progress
        _coacd_run_in_progress = False

        self.postprocess_colliders(context, self._coacd_results)
        self._coacd_results = []

        if len(self.new_colliders_list) < 1:
            self.report({'WARNING'}, 'No meshes to process!')
            if self._status_area is not None:
                self._status_area.tag_redraw()
            return

        if self.join_primitives:
            super().join_primitives(context)

        super().reset_to_initial_state(context)
        elapsed_time = self.get_time_elapsed()
        super().print_generation_time("Auto Convex (High Precision) Colliders", elapsed_time)
        self.report({'INFO'}, f"Auto Convex (High Precision) Colliders: {elapsed_time}")

        if self._status_area is not None:
            self._status_area.tag_redraw()

    def execute(self, context):
        """Kick off convex decomposition for the current selection. Does not
        block: it launches the first CoACD job and returns immediately,
        with _poll_coacd_process() (via bpy.app.timers) driving the rest."""
        global _coacd_run_in_progress
        if self._async_process is not None:
            # Already running (e.g. a hotkey re-triggered execute() while a
            # previous run is still in flight) - ignore rather than
            # overlapping a second subprocess run.
            return {'RUNNING_MODAL'}

        super().execute(context)

        coacd_exe, data_path = self.validate_paths_and_settings(context)
        if not coacd_exe or not data_path:
            return self.cancel(context)

        for obj in self.selected_objects.copy():
            obj.select_set(False)

        self._coacd_exe = coacd_exe
        self._coacd_data_path = data_path
        self._status_area = context.area
        self._invoke_window = context.window
        self._invoke_area = context.area
        self._invoke_region = next((r for r in context.area.regions if r.type == 'WINDOW'), None)
        self._coacd_run_id = str(id(self))
        self._coacd_pending_jobs = self.preprocess_objects_and_collect_data(context)
        self._coacd_results = []

        _coacd_run_in_progress = True
        self._start_next_coacd_job(context)

        return {'RUNNING_MODAL'}
