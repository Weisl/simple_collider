from math import radians

import bpy
import numpy as np
from bpy.types import Operator
from mathutils import Vector

from ..bmesh_operations.cylinder_generation import welzl
from .add_bounding_primitive import OBJECT_OT_add_bounding_object
from .utilities import get_sca_matrix, get_rot_matrix, get_loc_matrix

tmp_name = 'cylindrical_collider'

class OBJECT_OT_add_bounding_cylinder(OBJECT_OT_add_bounding_object, Operator):
    """Create cylindrical bounding collisions based on the selection"""
    bl_idname = "mesh.add_bounding_cylinder"
    bl_label = "Add Cylinder"
    bl_description = 'Create cylindrical colliders based on the selection'

    def generate_cylinder_object(self, context, radius, depth, location, rotation_euler=False):
        """
        Create cylindrical collider for every selected object in object mode.

        Args:
            context: Blender context.
            radius (float): Radius of the cylinder.
            depth (float): Depth of the cylinder.
            location (tuple): Location of the cylinder.
            rotation_euler (tuple, optional): Rotation of the cylinder.

        Returns:
            bpy.types.Object: The created cylindrical collider.
        """

        global tmp_name

        # add new cylindrical mesh
        bpy.ops.mesh.primitive_cylinder_add(vertices=self.current_settings_dic['cylinder_segments'],
                                            radius=radius,
                                            depth=depth,
                                            end_fill_type='TRIFAN',
                                            calc_uvs=True, )

        new_collider = context.object
        new_collider.name = tmp_name

        new_collider.location = location

        if rotation_euler:
            new_collider.rotation_euler = rotation_euler

        if self.cylinder_axis == 'X':
            new_collider.rotation_euler.rotate_axis("Y", radians(90))
        elif self.cylinder_axis == 'Y':
            new_collider.rotation_euler.rotate_axis("X", radians(90))

        return new_collider

    def get_used_vertices(self, base_ob, obj):
        if self.obj_mode == "EDIT" and base_ob.type == 'MESH' and self.active_obj.type == 'MESH' and not self.use_loose_mesh:
            return self.get_edit_mode_vertices_local_space(obj, use_modifiers=self.my_use_modifier_stack)
        else:
            return self.get_object_mode_vertices_local_space(obj, use_modifiers=self.my_use_modifier_stack)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
        Initialize the OBJECT_OT_add_bounding_cylinder operator.
        """
        super().__init__()
        self.shape = 'convex_shape'
        self.initial_shape = 'convex_shape'

        self.use_space = True
        self.use_modifier_stack = True
        self.use_global_local_switches = True

        # cylinder specific
        self.use_cylinder_segments = True
        self.use_cylinder_axis = True


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

        # change bounding object settings
        if event.type == 'G' and event.value == 'RELEASE':
            self.my_space = 'GLOBAL'
            self.execute(context)

        elif event.type == 'L' and event.value == 'RELEASE':
            self.my_space = 'LOCAL'
            self.execute(context)

        # define cylinder axis
        elif event.type == 'X' or event.type == 'Y' or event.type == 'Z' and event.value == 'RELEASE':
            self.cylinder_axis = event.type
            self.execute(context)

        # change bounding object settings
        if event.type == 'P' and event.value == 'RELEASE':
            self.my_use_modifier_stack = not self.my_use_modifier_stack
            self.execute(context)

        return {'RUNNING_MODAL'}

    def execute(self, context):
        # Call the parent class's execute method for any necessary initialization or cleanup
        super().execute(context)

        # Initialize lists to store collider data and vertex coordinates
        collider_data = []
        verts_co = []

        # Get the pre-processed mesh objects from the context
        objs = self.get_pre_processed_mesh_objs(context)

        # Iterate through each base object and its corresponding processed object
        for base_ob, obj in objs:
            # Initialize a dictionary to store data for the bounding cylinder
            bounding_cylinder_data = {}

            # Get the vertices that will be used for processing based on the mode and object type
            used_vertices = self.get_used_vertices(base_ob, obj)

            # If no vertices are found, skip to the next object
            if not used_vertices:
                continue

            # Decompose the object's world matrix into location, rotation, and scale components
            matrix_WS = obj.matrix_world
            loc, rot, sca = matrix_WS.decompose()

            creation_mode = self.creation_mode[self.creation_mode_idx] if self.obj_mode == 'OBJECT' else \
                self.creation_mode_edit[self.creation_mode_idx]

            if creation_mode in ['INDIVIDUAL'] or self.use_loose_mesh:
                coordinates = []
                height = []

                co = self.get_vertex_coordinates(
                    obj, self.my_space, used_vertices)
                bounding_box, center = self.generate_bounding_box(co)

                for vertex in used_vertices:

                    # Ignore Scale
                    if self.my_space == 'LOCAL':
                        v = vertex.co @ get_sca_matrix(sca)
                    else:
                        # Scale has to be applied before location
                        v = vertex.co @ get_sca_matrix(
                            sca) @ get_loc_matrix(loc) @ get_rot_matrix(rot)

                    if self.cylinder_axis == 'X':
                        coordinates.append([v.y, v.z])
                        height.append(v.x)
                    elif self.cylinder_axis == 'Y':
                        coordinates.append([v.x, v.z])
                        height.append(v.y)
                    elif self.cylinder_axis == 'Z':
                        coordinates.append([v.x, v.y])
                        height.append(v.z)

                if self.my_space == 'LOCAL':
                    center = sum((Vector(matrix_WS @ Vector(b))
                                  for b in bounding_box), Vector()) / 8.0
                else:
                    center = sum((Vector(b)
                                  for b in bounding_box), Vector()) / 8.0

                depth = abs(max(height) - min(height))
                nsphere = welzl(np.array(coordinates))
                radius = np.sqrt(nsphere.sqr_radius)

                bounding_cylinder_data['parent'] = base_ob
                bounding_cylinder_data['radius'] = radius
                bounding_cylinder_data['depth'] = depth
                bounding_cylinder_data['center_point'] = [
                    center[0], center[1], center[2]]
                collider_data.append(bounding_cylinder_data)

            else:  # if self.creation_mode[self.creation_mode_idx] == 'SELECTION':

                if self.shape == 'LOCAL':
                    ws_vtx_co = self.get_vertex_coordinates(obj, 'GLOBAL', used_vertices)
                    verts_co = verts_co + self.transform_vertex_space(ws_vtx_co, self.active_obj)
                else:
                    ws_vtx_co = self.get_vertex_coordinates(obj, 'GLOBAL', used_vertices)
                verts_co = verts_co + ws_vtx_co

                coordinates = []
                height = []

                bounding_box, center = self.generate_bounding_box(verts_co)
                center = sum((Vector(b) for b in bounding_box), Vector()) / 8.0

                for v in verts_co:
                    if self.cylinder_axis == 'X':
                        coordinates.append([v.y, v.z])
                        height.append(v.x)
                    elif self.cylinder_axis == 'Y':
                        coordinates.append([v.x, v.z])
                        height.append(v.y)
                    elif self.cylinder_axis == 'Z':
                        coordinates.append([v.x, v.y])
                        height.append(v.z)

                depth = abs(max(height) - min(height))

                nsphere = welzl(np.array(coordinates))
                radius = np.sqrt(nsphere.sqr_radius)

                bounding_cylinder_data['parent'] = self.active_obj
                bounding_cylinder_data['radius'] = radius
                bounding_cylinder_data['depth'] = depth
                bounding_cylinder_data['center_point'] = [
                    center[0], center[1], center[2]]
                collider_data = [bounding_cylinder_data]

        bpy.context.view_layer.objects.active = self.active_obj
        bpy.ops.object.mode_set(mode='OBJECT')

        for bounding_cylinder_data in collider_data:
            global tmp_name

            parent = bounding_cylinder_data['parent']
            radius = bounding_cylinder_data['radius']
            depth = bounding_cylinder_data['depth']
            center = bounding_cylinder_data['center_point']

            if self.my_space == 'GLOBAL':
                new_collider = self.generate_cylinder_object(
                    context, radius, depth, center)

            else:  # if self.my_space == 'LOCAL':
                new_collider = self.generate_cylinder_object(context, radius, depth, center,
                                                             rotation_euler=parent.rotation_euler)
                new_collider.scale = (1.0, 1.0, 1.0)

            self.new_colliders_list.append(new_collider)
            collections = parent.users_collection
            self.primitive_postprocessing(context, new_collider, collections)

            super().set_collider_name(new_collider, parent.name)
            self.custom_set_parent(context, parent, new_collider)

        # Merge all collider objects
        if self.join_primitives:
            super().join_primitives(context)

        super().reset_to_initial_state(context)
        elapsed_time = self.get_time_elapsed()
        super().print_generation_time("Convex Cylindrical Collider", elapsed_time)
        self.report(
            {'INFO'}, f"Convex Cylindrical Collider: {float(elapsed_time)}")

        return {'RUNNING_MODAL'}
