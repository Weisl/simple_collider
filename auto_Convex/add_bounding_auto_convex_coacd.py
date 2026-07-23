import os
import time
import subprocess

import bmesh
import bpy
from bpy.types import Operator

from ..bmesh_operations.mesh_edit import bmesh_join
from ..collider_shapes.add_bounding_primitive import OBJECT_OT_add_bounding_object


class COACD_OT_convex_decomposition(OBJECT_OT_add_bounding_object, Operator):
    bl_idname = 'collision.coacd'
    bl_label = 'Auto Convex (BETA)'
    bl_description = ('Create multiple convex hull colliders using CoACD (Collision-Aware Concavity and tree '
                      'search), the successor to V-HACD. This operator is still in BETA')
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

    def invoke(self, context, event):
        return super().invoke(context, event)

    def modal(self, context, event):
        status = super().modal(context, event)
        if status == {'FINISHED'}:
            return {'FINISHED'}
        if status == {'CANCELLED'}:
            return {'CANCELLED'}
        if status == {'PASS_THROUGH'}:
            return {'PASS_THROUGH'}

        if event.type == 'P' and event.value == 'RELEASE':
            self.my_use_modifier_stack = not self.my_use_modifier_stack
            self.execute(context)

        return {'RUNNING_MODAL'}

    def cancel(self, context):
        context.space_data.shading.color_type = self.color_type
        try:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
        except ValueError:
            pass
        return {'CANCELLED'}

    def validate_paths_and_settings(self, context):
        """Validate executable and data paths, and report errors if invalid."""
        overwrite_path = self.overwrite_executable_path(self.prefs.coacd_executable_path)
        coacd_exe = self.prefs.coacd_default_executable_path if not overwrite_path else overwrite_path
        data_path = self.set_temp_data_path(self.prefs.data_path)
        print(f"Using data path: {data_path}")

        if not coacd_exe:
            self.report({'ERROR'},
                        'CoACD executable is required for Auto Convex (BETA) to work. Please follow the '
                        'installation instructions and try it again')
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

        filename = ''.join(c for c in parent.name if c.isalnum() or c in (' ', '.', '_')).rstrip()
        obj_filename = os.path.join(data_path, f'{filename}.obj')

        print(f'\nExporting mesh for CoACD: {obj_filename}...')

        joined_obj.select_set(True)

        bpy.ops.wm.obj_export(filepath=obj_filename, check_existing=False, export_selected_objects=True,
                              export_materials=False, export_uv=False, export_normals=False,
                              forward_axis='Y', up_axis='Z')

        if self.prefs.debug:
            joined_obj.color = (1.0, 0.1, 0.1, 1.0)
            joined_obj.select_set(False)
        else:
            bpy.data.objects.remove(joined_obj)

        return obj_filename

    def run_coacd_decomposition(self, coacd_exe, obj_filename, data_path):
        """Run the CoACD decomposition process."""
        col_settings = bpy.context.scene.simple_collider
        prefs = self.prefs

        basename = os.path.splitext(os.path.basename(obj_filename))[0]
        output_filename = os.path.join(data_path, f'{basename}_coacd.obj')
        remesh_filename = os.path.join(data_path, f'{basename}_coacd_remesh.obj')

        cmd_line = (
            f'"{coacd_exe}" -i "{obj_filename}" -o "{output_filename}" -ro "{remesh_filename}" '
            f'-t {col_settings.coacd_threshold} -c {col_settings.coacd_maxConvexHulls} '
            f'-pm {prefs.coacd_preprocessMode} -pr {prefs.coacd_prepResolution} '
            f'-mi {prefs.coacd_mctsIterations} -md {prefs.coacd_mctsDepth} -mn {prefs.coacd_mctsNodes} '
            f'-r {prefs.coacd_resolution}'
        )

        if col_settings.coacd_decimate:
            cmd_line += f' -d -dt {col_settings.coacd_maxHullVertCount}'
        if prefs.coacd_noMerge:
            cmd_line += ' -nm'
        if prefs.coacd_pca:
            cmd_line += ' --pca'

        print('Running CoACD...\n{}\n'.format(cmd_line))
        print(f"Using data path for CoACD: {data_path}")

        coacd_process = subprocess.Popen(cmd_line, bufsize=-1, close_fds=True, shell=True, cwd=data_path)
        coacd_process.wait()

        if not os.path.isfile(output_filename):
            return None

        return output_filename

    def import_decomposed_meshes(self, obj_path):
        """Import the decomposed meshes from the CoACD output OBJ file."""
        imported = []

        bpy.ops.wm.obj_import(filepath=obj_path, forward_axis='Y', up_axis='Z')
        imported.extend(bpy.context.selected_objects)

        for ob in imported:
            ob.select_set(False)

        return imported

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

    def execute(self, context):
        """Main execution method for CoACD convex decomposition."""
        super().execute(context)

        coacd_exe, data_path = self.validate_paths_and_settings(context)
        if not coacd_exe or not data_path:
            return self.cancel(context)

        for obj in self.selected_objects.copy():
            obj.select_set(False)

        collider_data = self.preprocess_objects_and_collect_data(context)

        convex_decomposition_data = []

        for convex_collision_data in collider_data:
            parent = convex_collision_data['parent']
            mesh = convex_collision_data['mesh']

            obj_filename = self.export_mesh_for_coacd(context, parent, mesh, data_path)
            if obj_filename is None:
                return self.cancel(context)

            output_obj = self.run_coacd_decomposition(coacd_exe, obj_filename, data_path)

            if output_obj is None:
                self.report({'WARNING'}, f'CoACD failed to generate colliders for {parent.name}')
                bpy.data.meshes.remove(mesh)
                continue

            imported = self.import_decomposed_meshes(output_obj)

            convex_collisions_data = {'colliders': imported, 'parent': parent, 'mtx_world': parent.matrix_world.copy()}
            convex_decomposition_data.append(convex_collisions_data)

            bpy.data.meshes.remove(mesh)

        self.postprocess_colliders(context, convex_decomposition_data)

        if len(self.new_colliders_list) < 1:
            self.report({'WARNING'}, 'No meshes to process!')
            return {'CANCELLED'}

        if self.join_primitives:
            super().join_primitives(context)

        super().reset_to_initial_state(context)
        elapsed_time = self.get_time_elapsed()
        super().print_generation_time("Auto Convex (BETA) Colliders", elapsed_time)
        self.report({'INFO'}, f"Auto Convex (BETA) Colliders: {elapsed_time}")

        return {'FINISHED'}
