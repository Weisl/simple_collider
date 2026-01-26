import os
import time
import subprocess

import bmesh
import bpy
from bpy.types import Operator

from ..bmesh_operations.mesh_edit import bmesh_join
from ..collider_shapes.add_bounding_primitive import OBJECT_OT_add_bounding_object


class VHACD_OT_convex_decomposition(OBJECT_OT_add_bounding_object, Operator):
    bl_idname = 'collision.vhacd'
    bl_label = 'Convex Decomposition'
    bl_description = ('Create multiple convex hull colliders to represent any object using Hierarchical Approximate '
                      'Convex Decomposition')
    bl_options = {'REGISTER', 'PRESET'}

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
        super().invoke(context, event)
        return {'RUNNING_MODAL'}

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
        bpy.context.scene.collection.objects.link(joined_obj)

        filename = ''.join(c for c in parent.name if c.isalnum() or c in (' ', '.', '_')).rstrip()
        obj_filename = os.path.join(data_path, f'{filename}.obj')

        print(f'\nExporting mesh for V-HACD: {obj_filename}...')

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

    def run_vhacd_decomposition(self, vhacd_exe, obj_filename, data_path, export_time):
        """Run the V-HACD decomposition process."""
        col_settings = bpy.context.scene.simple_collider

        cmd_line = (
            f'"{vhacd_exe}" "{obj_filename}" -h {col_settings.maxHullAmount} -v {col_settings.maxHullVertCount} '
            f'-o obj -g 1 -r {col_settings.voxelResolution} -e {self.prefs.vhacd_volumneErrorPercent} '
            f'-d {self.prefs.vhacd_maxRecursionDepth} -s {"true" if col_settings.vhacd_shrinkwrap else "false"} '
            f'-f {self.prefs.vhacd_fillMode} -l {self.prefs.vhacd_minEdgeLength} '
            f'-p {"true" if self.prefs.vhacd_optimalSplitPlane else "false"} -g true'
        )

        print('Running V-HACD...\n{}\n'.format(cmd_line))
        print(f"Using data path for V-HACD: {data_path}")

        vhacd_process = subprocess.Popen(cmd_line, bufsize=-1, close_fds=True, shell=True, cwd=data_path)
        vhacd_process.wait()

        # Collect newly created OBJ files
        dir_files = os.listdir(data_path)
        obj_list = []
        for file in dir_files:
            if file.endswith('.obj'):
                obj_path = os.path.join(data_path, file)
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
        """Main execution method for convex decomposition."""
        super().execute(context)

        vhacd_exe, data_path = self.validate_paths_and_settings(context)
        if not vhacd_exe or not data_path:
            return self.cancel(context)

        for obj in self.selected_objects.copy():
            obj.select_set(False)

        collider_data = self.preprocess_objects_and_collect_data(context)

        convex_decomposition_data = []

        for convex_collision_data in collider_data:
            parent = convex_collision_data['parent']
            mesh = convex_collision_data['mesh']

            obj_filename = self.export_mesh_for_vhacd(context, parent, mesh, data_path)
            if obj_filename is None:
                return self.cancel(context)

            export_time = time.time()

            obj_list = self.run_vhacd_decomposition(vhacd_exe, obj_filename, data_path, export_time)

            imported = self.import_decomposed_meshes(obj_list)

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
        super().print_generation_time("Auto Convex Colliders", elapsed_time)
        self.report({'INFO'}, f"Auto Convex Colliders: {elapsed_time}")

        return {'FINISHED'}
