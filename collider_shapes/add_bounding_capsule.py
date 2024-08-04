from math import radians
import bpy
from bpy.types import Operator
from mathutils import Vector, Matrix
from .add_bounding_primitive import OBJECT_OT_add_bounding_object
from .utilities import get_sca_matrix
from ..bmesh_operations.capsule_generation import create_capsule_data, calculate_radius_height, mesh_data_to_bmesh

tmp_name = 'capsule_collider'


class OBJECT_OT_add_bounding_capsule(OBJECT_OT_add_bounding_object, Operator):
    """Create bounding capsule collider based on the selection"""
    bl_idname = "mesh.add_bounding_capsule"
    bl_label = "Add Capsule (Beta)"
    bl_description = 'Create bounding capsule colliders based on the selection'

    def __init__(self):
        super().__init__()
        self.use_space = True
        self.use_modifier_stack = True
        self.use_global_local_switches = True
        self.use_capsule_axis = True
        self.use_capsule_segments = True
        self.use_height_multiplier = True
        self.use_width_multiplier = True
        self.shape = 'capsule_shape'
        self.initial_shape = 'capsule_shape'

    def invoke(self, context, event):
        super().invoke(context, event)
        return {'RUNNING_MODAL'}

    def set_modal_state(self, cylinder_segments_active=False, displace_active=False, decimate_active=False,
                        opacity_active=False, sphere_segments_active=False, capsule_segments_active=False,
                        remesh_active=False, height_active=False, width_active=False):
        super().set_modal_state(cylinder_segments_active, displace_active, decimate_active,
                                opacity_active, sphere_segments_active, capsule_segments_active,
                                remesh_active, height_active, width_active)
        self.capsule_segments_active = capsule_segments_active

    def modal(self, context, event):
        status = super().modal(context, event)

        if status == {'FINISHED'}:
            return {'FINISHED'}
        if status == {'CANCELLED'}:
            return {'CANCELLED'}
        if status == {'PASS_THROUGH'}:
            return {'PASS_THROUGH'}

        # change bounding object settings
        if event.type == 'G' and event.value == 'RELEASE':
            self.my_space = 'GLOBAL'
            self.execute(context)

        elif event.type == 'L' and event.value == 'RELEASE':
            self.my_space = 'LOCAL'
            self.execute(context)

        # change bounding object settings
        if event.type == 'R' and event.value == 'RELEASE':
            self.set_modal_state(capsule_segments_active=not self.capsule_segments_active)
            self.execute(context)

        # change bounding object settings
        if event.type == 'P' and event.value == 'RELEASE':
            self.my_use_modifier_stack = not self.my_use_modifier_stack
            self.execute(context)

        elif event.type in {'X', 'Y', 'Z'} and event.value == 'RELEASE':
            # define cylinder axis
            self.cylinder_axis = event.type
            self.execute(context)

        return {'RUNNING_MODAL'}

    def execute(self, context):
        super().execute(context)

        # List for storing dictionaries of data used to generate the collision meshes
        collider_data = []
        selection_vertex_coords = []

        objects = self.get_pre_processed_mesh_objs(context, default_world_spc=True)

        # iterate over base objects
        for base_object, obj in objects:

            context.view_layer.objects.active = obj
            bounding_capsule_data = {}

            if self.obj_mode == "EDIT" and base_object.type == 'MESH' and self.active_obj.type == 'MESH' and not self.use_loose_mesh:
                used_vertices = self.get_edit_mode_vertices_local_space(obj, use_modifiers=self.my_use_modifier_stack)

            else:  # self.obj_mode  == "OBJECT" or self.use_loose_mesh == True:
                used_vertices = self.get_object_mode_vertices_local_space(obj, use_modifiers=self.my_use_modifier_stack)

            if used_vertices is None:  # Skip object if there is no Mesh data to create the collider
                continue

            # Save base object coordinates
            matrix_world_space = obj.matrix_world
            location, rotation, scale = matrix_world_space.decompose()

            creation_mode = self.creation_mode[self.creation_mode_idx] if self.obj_mode == 'OBJECT' else \
                self.creation_mode_edit[self.creation_mode_idx]

            vertex_coords_local = self.get_vertex_coordinates(obj, 'LOCAL', used_vertices)
            vertex_coords_global = self.get_vertex_coordinates(obj, 'GLOBAL', used_vertices)

            if creation_mode in ['INDIVIDUAL'] or self.use_loose_mesh:
                vertex_coords = vertex_coords_global if self.my_space == 'GLOBAL' else vertex_coords_local
                bounding_capsule_data = {'parent': base_object,
                                         'vertex_coords': vertex_coords}
                collider_data.append(bounding_capsule_data)

            else:  # creation_mode == 'SELECTION':
                # add all vertices in global space to the list
                selection_vertex_coords.extend(vertex_coords_global)

        if creation_mode == 'SELECTION':
            bounding_capsule_data = {'parent': self.active_obj,
                                     'vertex_coords': selection_vertex_coords}
            collider_data.append(bounding_capsule_data)

        bpy.ops.object.mode_set(mode='OBJECT')

        for bounding_capsule_data in collider_data:
            parent = bounding_capsule_data['parent']
            vertex_coords = bounding_capsule_data['vertex_coords']

            if creation_mode == 'INDIVIDUAL' or self.use_loose_mesh:
                # coordinates are based on self.my_space
                radius, height, center_capsule, rotation_matrix_4x4 = calculate_radius_height(vertex_coords, self.cylinder_axis)

                capsule_data = create_capsule_data(longitudes=self.current_settings_dic['capsule_segments'],
                                                   latitudes=int(self.current_settings_dic['capsule_segments']),
                                                   radius=radius * self.current_settings_dic['width_mult'],
                                                   depth=height * self.current_settings_dic['height_mult'], uv_profile="FIXED")

                bm = mesh_data_to_bmesh(
                    vs=capsule_data["vs"],
                    vts=capsule_data["vts"],
                    vns=capsule_data["vns"],
                    v_indices=capsule_data["v_indices"],
                    vt_indices=capsule_data["vt_indices"],
                    vn_indices=capsule_data["vn_indices"])

                mesh_data = bpy.data.meshes.new("Capsule")
                bm.to_mesh(mesh_data)
                bm.free()

                new_collider = bpy.data.objects.new(mesh_data.name, mesh_data)

                # it works when the origin is centered
                if self.my_space == 'LOCAL':
                    # align object to parent object
                    new_collider.matrix_world = base_object.matrix_world.copy()
                    # offset the object by the capsule center
                    translation_matrix = Matrix.Translation(center_capsule)
                    # Apply the translation matrix to the new collider
                    new_collider.matrix_world = new_collider.matrix_world @ translation_matrix
                    # Apply the rotation matrix to the new collider
                    new_collider.matrix_world = new_collider.matrix_world @ rotation_matrix_4x4



                self.new_colliders_list.append(new_collider)
                collections = parent.users_collection
                self.primitive_postprocessing(context, new_collider, collections)

                parent_name = parent.name
                super().set_collider_name(new_collider, parent_name)
                self.custom_set_parent(context, parent, new_collider)

            if self.join_primitives:
                super().join_primitives(context)

        super().reset_to_initial_state(context)
        elapsed_time = self.get_time_elapsed()
        super().print_generation_time("Capsule Collider", elapsed_time)
        self.report({'INFO'}, f"Capsule Collider: {float(elapsed_time)}")

        return {'RUNNING_MODAL'}
