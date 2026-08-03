import os
import re
import time

import bmesh
import bpy
from bpy.types import Operator

from ..bmesh_operations.mesh_edit import bmesh_join
from ..collider_shapes.add_bounding_primitive import OBJECT_OT_add_bounding_object, _remove_draw_handle

# How often the V-HACD subprocess is polled for completion while it's
# running. Polling (rather than Popen.wait()) is what keeps Blender's UI
# thread responsive - see COACD_OT_convex_decomposition/#660, which this
# mirrors: V-HACD ran synchronously the same way CoACD used to, and can take
# anywhere from a fraction of a second to several minutes on complex meshes.
# This also drives how often the status overlay redraws (draw_async_job_
# overlay()'s scrolling stripes) - process.poll() and draining the (usually
# empty) progress queue are both cheap, so this runs at a plain 60fps redraw
# cadence for smooth animation rather than the coarser interval a "just
# check if it's done yet" poll alone would need.
VHACD_POLL_INTERVAL_SECONDS = 1 / 60

# V-HACD prints its own progress to stdout as e.g.
# "[PERFORMING_DECOMPOSITION] : 50% : 0% : Performing recursive decomposition
# of convex hulls", using '\r' between updates the way a terminal progress
# bar would (see OBJECT_OT_add_bounding_object._launch_async_process()'s
# reader, which splits on '\r' as well as '\n' for exactly this). Parsed by
# _parse_progress_line() into a short status string for the shared overlay.
_VHACD_PROGRESS_RE = re.compile(r'^\[(\S+)\s*\]\s*:\s*(\d+)%\s*:\s*(\d+)%\s*:\s*(.+)$')

# True while any VHACD_OT_convex_decomposition instance has a job in flight.
# Module-level (not per-instance) for the same reason as CoACD's
# _coacd_run_in_progress (see add_bounding_auto_convex_coacd.py): invoke()
# creates a brand new instance every time the operator is triggered, so an
# instance attribute can't stop a *second*, independent invocation from
# starting while Blender no longer looks busy.
_vhacd_run_in_progress = False


class VHACD_OT_convex_decomposition(OBJECT_OT_add_bounding_object, Operator):
    bl_idname = 'collision.vhacd'
    bl_label = 'Convex Decomposition'
    bl_description = ('Create multiple convex hull colliders to represent any object using Hierarchical Approximate '
                      'Convex Decomposition')
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

        # Async V-HACD job state, mirroring COACD_OT_convex_decomposition
        # (#660). _async_process/_async_start_time are the generic names the
        # shared status overlay (draw_async_job_overlay() in
        # add_bounding_primitive) looks for via getattr() - CoACD uses the
        # same names so both backends drive the same overlay.
        self._async_process = None
        self._async_start_time = 0.0
        self._async_job_label = 'V-HACD'
        self._vhacd_exe = None
        self._vhacd_data_path = None
        self._vhacd_pending_jobs = []
        self._vhacd_results = []
        self._vhacd_job_ctx = None
        self._status_area = None

        # bpy.app.timers callbacks (see _poll_vhacd_process()) have no
        # guaranteed context - see the identical note in
        # COACD_OT_convex_decomposition.__init__() for why this is captured
        # here and overridden into for every downstream async step.
        self._invoke_window = None
        self._invoke_area = None
        self._invoke_region = None

    def invoke(self, context, event):
        if _vhacd_run_in_progress:
            self.report({'ERROR'}, 'Auto Convex is already running - wait for it to finish, or select it and '
                                    'press Escape to cancel, before starting another run')
            return {'CANCELLED'}
        return super().invoke(context, event)

    def modal(self, context, event):
        if self._async_process is not None:
            # A V-HACD job is in flight: swallow all input except viewport
            # navigation (still allowed so the user isn't locked out of
            # looking around while it runs) and cancel. Everything else -
            # including LEFTMOUSE/RET confirm - is intentionally ignored,
            # since the colliders this operator would finalize don't exist
            # yet.
            if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
                return {'PASS_THROUGH'}
            if event.type in {'RIGHTMOUSE', 'ESC'}:
                self._cancel_vhacd_job(context)
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
        self._cancel_vhacd_job(context)
        context.space_data.shading.color_type = self.color_type
        _remove_draw_handle(self._handle)
        return {'CANCELLED'}

    def validate_paths_and_settings(self, context):
        """Validate executable and data paths, and report errors if invalid."""
        overwrite_path = self.overwrite_executable_path(self.prefs.executable_path)
        vhacd_exe = self.prefs.default_executable_path if not overwrite_path else overwrite_path
        data_path = self.set_temp_data_path(self.prefs.data_path)
        print(f"Using data path: {data_path}")

        if not vhacd_exe:
            self.report({'ERROR'},
                        'V-HACD executable is required for Auto Convex to work. Please follow the installation '
                        'instructions and try it again')
            return None, None
        if not data_path:
            self.report({'ERROR'}, 'Invalid temporary data path')
            return None, None

        return vhacd_exe, data_path

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

    def export_mesh_for_vhacd(self, context, parent, mesh, data_path):
        """Export the mesh to OBJ format for V-HACD processing."""
        joined_obj = bpy.data.objects.new('debug_joined_mesh', mesh.copy())
        context.scene.collection.objects.link(joined_obj)

        filename = ''.join(c for c in parent.name if c.isalnum() or c in (' ', '.', '_')).rstrip()
        obj_filename = os.path.join(data_path, f'{filename}.obj')

        print(f'\nExporting mesh for V-HACD: {obj_filename}...')

        joined_obj.select_set(True)

        bpy.ops.wm.obj_export(filepath=obj_filename, check_existing=False, export_selected_objects=True,
                              export_materials=False, export_uv=False, export_normals=False,
                              forward_axis='Y', up_axis='Z')

        bpy.data.objects.remove(joined_obj)

        return obj_filename

    def _parse_progress_line(self, line):
        """Override of the base class hook (see _drain_async_progress()):
        V-HACD's stdout format - see _VHACD_PROGRESS_RE above."""
        m = _VHACD_PROGRESS_RE.match(line.strip())
        if not m:
            return None
        overall_pct = m.group(2)
        description = m.group(4).strip()
        return f'{description} {overall_pct}%'

    def _start_next_vhacd_job(self, context):
        """Pop the next collider off the queue and launch V-HACD on it
        without blocking. If the queue is empty, the whole run is done."""
        if not self._vhacd_pending_jobs:
            self._finish_vhacd_run(context)
            return

        convex_collision_data = self._vhacd_pending_jobs.pop(0)
        parent = convex_collision_data['parent']
        mesh = convex_collision_data['mesh']
        mtx_world = convex_collision_data['mtx_world']

        obj_filename = self.export_mesh_for_vhacd(context, parent, mesh, self._vhacd_data_path)
        export_time = time.time()

        col_settings = context.scene.simple_collider
        prefs = self.prefs

        cmd = [
            self._vhacd_exe, obj_filename,
            '-h', str(col_settings.maxHullAmount), '-v', str(col_settings.maxHullVertCount),
            '-o', 'obj', '-g', '1', '-r', str(col_settings.voxelResolution),
            '-e', str(prefs.vhacd_volumneErrorPercent),
            '-d', str(prefs.vhacd_maxRecursionDepth),
            '-s', 'true' if col_settings.vhacd_shrinkwrap else 'false',
            '-f', prefs.vhacd_fillMode, '-l', str(prefs.vhacd_minEdgeLength),
            '-p', 'true' if prefs.vhacd_optimalSplitPlane else 'false', '-g', 'true',
        ]

        print('Running V-HACD...\n{}\n'.format(' '.join(cmd)))
        print(f"Using data path for V-HACD: {self._vhacd_data_path}")

        # No shell=True: V-HACD is launched directly (not via an intermediate
        # cmd.exe/sh -c) so that killing this Popen on cancel actually kills
        # the V-HACD process itself rather than leaving it running detached.
        process = self._launch_async_process(cmd, self._vhacd_data_path)

        self._async_process = process
        self._vhacd_job_ctx = {
            'parent': parent,
            'mesh': mesh,
            'mtx_world': mtx_world,
            'obj_filename': obj_filename,
            'export_time': export_time,
        }
        self._async_start_time = time.time()
        bpy.app.timers.register(self._poll_vhacd_process, first_interval=VHACD_POLL_INTERVAL_SECONDS)

    def _poll_vhacd_process(self):
        """bpy.app.timers callback: check whether the current V-HACD
        subprocess has finished, without blocking Blender's main thread.
        Re-arms itself via its return value for as long as the process is
        still running."""
        global _vhacd_run_in_progress
        try:
            process = self._async_process
            if process is None:
                return None

            if process.poll() is None:
                self._drain_async_progress()
                if self._status_area is not None:
                    self._status_area.tag_redraw()
                return VHACD_POLL_INTERVAL_SECONDS

            self._async_process = None

            # bpy.context here has no guaranteed space_data - see the
            # identical note in COACD_OT_convex_decomposition._poll_coacd_process().
            with bpy.context.temp_override(window=self._invoke_window, area=self._invoke_area,
                                           region=self._invoke_region):
                self._handle_vhacd_job_finished(bpy.context)
        except ReferenceError:
            # operator has already finished/cancelled and its RNA was freed
            _vhacd_run_in_progress = False
        except Exception:
            # Whatever went wrong, never leave the module-level run lock
            # stuck - that would permanently block every future Auto Convex
            # invocation until Blender restarts. Still re-raised so the
            # actual error is printed to the console as usual.
            _vhacd_run_in_progress = False
            raise
        return None

    def _collect_vhacd_output_files(self, obj_filename, export_time):
        """Collect newly created OBJ files V-HACD wrote to the data path."""
        dir_files = os.listdir(self._vhacd_data_path)
        obj_list = []
        for file in dir_files:
            if file.endswith('.obj'):
                obj_path = os.path.join(self._vhacd_data_path, file)
                file_time = os.path.getmtime(obj_path)
                if file_time > export_time:
                    obj_list.append(obj_path)

        # Exclude the input OBJ file and any variants (e.g., Cube000.obj)
        input_basename = os.path.splitext(os.path.basename(obj_filename))[0]
        obj_list = [p for p in obj_list if not os.path.basename(p).startswith(input_basename)]

        return obj_list

    def import_decomposed_meshes(self, obj_list):
        """Import the decomposed meshes from OBJ files."""
        imported = []

        for obj_path in obj_list:
            bpy.ops.wm.obj_import(filepath=obj_path, forward_axis='Y', up_axis='Z')
            imported.extend(bpy.context.selected_objects)

        for ob in imported:
            ob.select_set(False)

        return imported

    def _handle_vhacd_job_finished(self, context):
        """Called once the decomposition subprocess for one collider has
        exited. Imports whatever V-HACD produced and moves on to the next
        queued collider, or finishes the run if none are left."""
        job = self._vhacd_job_ctx
        parent = job['parent']
        mesh = job['mesh']
        mtx_world = job['mtx_world']
        obj_filename = job['obj_filename']
        export_time = job['export_time']

        obj_list = self._collect_vhacd_output_files(obj_filename, export_time)
        imported = self.import_decomposed_meshes(obj_list)

        self._vhacd_results.append({'colliders': imported, 'parent': parent, 'mtx_world': mtx_world})
        bpy.data.meshes.remove(mesh)
        self._vhacd_job_ctx = None
        self._start_next_vhacd_job(context)

    def _cancel_vhacd_job(self, context):
        """Kill any in-flight V-HACD subprocess and drop all queued/partial
        state for the current run. Called from modal()'s ESC/RIGHTMOUSE
        handling and from cancel()."""
        global _vhacd_run_in_progress
        _vhacd_run_in_progress = False

        if self._async_process is not None:
            try:
                self._async_process.kill()
                self._async_process.wait(timeout=5)
            except Exception:
                pass
            self._async_process = None

        if self._vhacd_job_ctx is not None:
            mesh = self._vhacd_job_ctx.get('mesh')
            if mesh is not None:
                try:
                    bpy.data.meshes.remove(mesh)
                except ReferenceError:
                    pass
            self._vhacd_job_ctx = None

        for result in self._vhacd_results:
            self.remove_objects(result['colliders'])

        self._vhacd_pending_jobs = []
        self._vhacd_results = []

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

    def _finish_vhacd_run(self, context):
        """Called once every queued collider has been decomposed. Mirrors
        what the old synchronous execute() did after its blocking loop
        finished."""
        global _vhacd_run_in_progress
        _vhacd_run_in_progress = False

        self.postprocess_colliders(context, self._vhacd_results)
        self._vhacd_results = []

        if len(self.new_colliders_list) < 1:
            self.report({'WARNING'}, 'No meshes to process!')
            if self._status_area is not None:
                self._status_area.tag_redraw()
            return

        if self.join_primitives:
            super().join_primitives(context)

        super().reset_to_initial_state(context)
        elapsed_time = self.get_time_elapsed()
        super().print_generation_time("Auto Convex Colliders", elapsed_time)
        self.report({'INFO'}, f"Auto Convex Colliders: {elapsed_time}")

        if self._status_area is not None:
            self._status_area.tag_redraw()

    def execute(self, context):
        """Kick off convex decomposition for the current selection. Does not
        block: it launches the first V-HACD job and returns immediately,
        with _poll_vhacd_process() (via bpy.app.timers) driving the rest."""
        global _vhacd_run_in_progress
        if self._async_process is not None:
            # Already running (e.g. a hotkey re-triggered execute() while a
            # previous run is still in flight) - ignore rather than
            # overlapping a second subprocess run.
            return {'RUNNING_MODAL'}

        super().execute(context)

        vhacd_exe, data_path = self.validate_paths_and_settings(context)
        if not vhacd_exe or not data_path:
            return self.cancel(context)

        for obj in self.selected_objects.copy():
            obj.select_set(False)

        self._vhacd_exe = vhacd_exe
        self._vhacd_data_path = data_path
        self._status_area = context.area
        self._invoke_window = context.window
        self._invoke_area = context.area
        self._invoke_region = next((r for r in context.area.regions if r.type == 'WINDOW'), None)
        self._vhacd_pending_jobs = self.preprocess_objects_and_collect_data(context)
        self._vhacd_results = []

        _vhacd_run_in_progress = True
        self._start_next_vhacd_job(context)

        return {'RUNNING_MODAL'}
