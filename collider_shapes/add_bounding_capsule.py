from math import radians

import bpy
from bpy.types import Operator
from mathutils import Vector, Matrix

from .add_bounding_primitive import OBJECT_OT_add_bounding_object
from .utilities import get_sca_matrix, get_rot_matrix, get_loc_matrix
from ..bmesh_operations.capsule_generation import create_capsule, calculate_radius_height, mesh_data_to_bmesh

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
        vertices_coordinates = []

        objects = self.get_pre_processed_mesh_objs(context, default_world_spc=True)

        for base_object, obj in objects:

            context.view_layer.objects.active = obj
            bounding_capsule_data = {}

            if self.obj_mode == "EDIT" and base_object.type == 'MESH' and self.active_obj.type == 'MESH' and not self.use_loose_mesh:
                used_vertices = self.get_vertices_edit(obj, use_modifiers=self.my_use_modifier_stack)

            else:  # self.obj_mode  == "OBJECT" or self.use_loose_mesh == True:
                used_vertices = self.get_object_vertices(obj, use_modifiers=self.my_use_modifier_stack)

            if used_vertices is None:  # Skip object if there is no Mesh data to create the collider
                continue

            # Save base object coordinates
            matrix_world_space = obj.matrix_world
            location, rotation, scale = matrix_world_space.decompose()

            creation_mode = self.creation_mode[self.creation_mode_idx] if self.obj_mode == 'OBJECT' else \
                self.creation_mode_edit[self.creation_mode_idx]

            if creation_mode in ['INDIVIDUAL'] or self.use_loose_mesh:
                # used_vertices uses local space.
                coordinates = []

                for vertex in used_vertices:
                    if self.my_space == 'LOCAL':
                        vertex_position = vertex.co @ get_sca_matrix(scale)
                    else:
                        vertex_position = vertex.co @ matrix_world_space

                    if self.cylinder_axis == 'Z' or self.use_loose_mesh:
                        coordinates.append([vertex_position.x, vertex_position.y, vertex_position.z])
                    elif self.cylinder_axis == 'X':
                        coordinates.append([vertex_position.y, vertex_position.z, vertex_position.x])
                    elif self.cylinder_axis == 'Y':
                        coordinates.append([vertex_position.x, vertex_position.z, vertex_position.y])

                center = sum((Vector(matrix_world_space @ Vector(v)) for v in coordinates), Vector()) / len(
                    used_vertices)

                bounding_capsule_data['parent'] = base_object
                bounding_capsule_data['verts_loc'] = coordinates
                bounding_capsule_data['center_point'] = [center[0], center[1], center[2]]
                collider_data.append(bounding_capsule_data)
            else:  # if self.creation_mode[self.creation_mode_idx] == 'SELECTION':
                world_space_vertex_coords = self.get_point_positions(obj, 'GLOBAL', used_vertices)
                vertices_coordinates.extend(world_space_vertex_coords)

        if vertices_coordinates:
            center = sum((Vector(v_co) for v_co in vertices_coordinates), Vector()) / len(vertices_coordinates)
            bounding_capsule_data = {
                'parent': self.active_obj,
                'verts_loc': vertices_coordinates,
                'center_point': [center[0], center[1], center[2]]
            }
            collider_data = [bounding_capsule_data]

        bpy.ops.object.mode_set(mode='OBJECT')

        for bounding_capsule_data in collider_data:
            parent = bounding_capsule_data['parent']
            verts_loc = bounding_capsule_data['verts_loc']
            center = bounding_capsule_data['center_point']

            radius, height, center_capsule, rotation_matrix_4x4 = calculate_radius_height(verts_loc, self.cylinder_axis)
            data = create_capsule(longitudes=self.current_settings_dic['capsule_segments'],
                                  latitudes=int(self.current_settings_dic['capsule_segments']),
                                  radius=radius * self.current_settings_dic['width_mult'],
                                  depth=height * self.current_settings_dic['height_mult'], uv_profile="FIXED")
            bm = mesh_data_to_bmesh(
                vs=data["vs"],
                vts=data["vts"],
                vns=data["vns"],
                v_indices=data["v_indices"],
                vt_indices=data["vt_indices"],
                vn_indices=data["vn_indices"])

            mesh_data = bpy.data.meshes.new("Capsule")
            bm.to_mesh(mesh_data)
            bm.free()

            new_collider = bpy.data.objects.new(mesh_data.name, mesh_data)

            creation_mode = self.creation_mode[self.creation_mode_idx] if self.obj_mode == 'OBJECT' else \
                self.creation_mode_edit[self.creation_mode_idx]

            if self.my_space == 'LOCAL' and (creation_mode in ['INDIVIDUAL'] or self.use_loose_mesh):
                new_collider.rotation_euler = parent.rotation_euler
                new_collider.matrix_world = rotation_matrix_4x4 @ Matrix.Translation(center_capsule)
                new_collider.location = center
            else:
                if self.my_space == 'LOCAL':
                    active_obj_matrix_world = self.active_obj.matrix_world
                    center = active_obj_matrix_world.inverted() @ Vector(center)
                    new_collider.location = center
                else:
                    new_collider.location = center

            if self.cylinder_axis == 'X':
                new_collider.rotation_euler.rotate_axis("Y", radians(90))
            elif self.cylinder_axis == 'Y':
                new_collider.rotation_euler.rotate_axis("X", radians(90))

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
