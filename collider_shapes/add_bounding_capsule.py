import bpy
import numpy as np
from bpy.types import Operator
from mathutils import Vector

from .add_bounding_primitive import OBJECT_OT_add_bounding_object
from .utilities import get_sca_matrix, get_rot_matrix, get_loc_matrix
from ..bmesh_operations.capsule_generation import create_capsule_data, mesh_data_to_bmesh
from ..bmesh_operations.cylinder_generation import welzl

tmp_name = 'capsule_collider'

class OBJECT_OT_add_bounding_capsule(OBJECT_OT_add_bounding_object, Operator):
    """Create bounding capsule collider based on the selection"""
    bl_idname = "mesh.add_bounding_capsule"
    bl_label = "Add Capsule (Beta)"
    bl_description = 'Create bounding capsule colliders based on the selection'

    def __init__(self):
        self.shape = 'capsule_shape'
        self.initial_shape = 'capsule_shape'

        super().__init__()
        self.use_space = True
        self.use_modifier_stack = True
        self.use_global_local_switches = True

        # Capsule specific
        self.use_capsule_axis = True
        self.use_capsule_segments = True
        self.use_height_multiplier = True
        self.use_width_multiplier = True

    def get_used_vertices(self, base_ob, obj):
        if self.obj_mode == "EDIT" and base_ob.type == 'MESH' and self.active_obj.type == 'MESH' and not self.use_loose_mesh:
            return self.get_edit_mode_vertices_local_space(obj, use_modifiers=self.my_use_modifier_stack)
        else:
            return self.get_object_mode_vertices_local_space(obj, use_modifiers=self.my_use_modifier_stack)

    def set_modal_state(self, cylinder_segments_active=False, displace_active=False, decimate_active=False,
                        opacity_active=False, sphere_segments_active=False, capsule_segments_active=False,
                        remesh_active=False, height_active=False, width_active=False):
        super().set_modal_state(cylinder_segments_active, displace_active, decimate_active, opacity_active,
                                sphere_segments_active, capsule_segments_active, remesh_active, height_active,
                                width_active)
        self.capsule_segments_active = capsule_segments_active

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
        # Call the parent class's execute method for necessary setup
        super().execute(context)

        # Initialize lists to store collider data and vertex coordinates
        collider_data = []
        verts_co = []

        # Get the pre-processed mesh objects from the context
        objs = self.get_pre_processed_mesh_objs(context)

        for base_ob, obj in objs:
            # Initialize a dictionary to store data for the bounding cylinder
            bounding_capsule_data = {}

            used_vertices = self.get_used_vertices(base_ob, obj)

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

                co = self.get_vertex_coordinates(obj, self.my_space, used_vertices)
                bounding_box, center = self.generate_bounding_box(co)

                for vertex in used_vertices:

                    # Ignore Scale
                    if self.my_space == 'LOCAL':
                        v = vertex.co @ get_sca_matrix(sca)
                    else:
                        # Scale has to be applied before location
                        v = vertex.co @ get_sca_matrix(sca) @ get_loc_matrix(loc) @ get_rot_matrix(rot)

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
                    center = sum((Vector(matrix_WS @ Vector(b)) for b in bounding_box), Vector()) / 8.0
                else:
                    center = sum((Vector(b) for b in bounding_box), Vector()) / 8.0

                depth = abs(max(height) - min(height))
                nsphere = welzl(np.array(coordinates))
                radius = np.sqrt(nsphere.sqr_radius)

                bounding_capsule_data['parent'] = base_ob
                bounding_capsule_data['radius'] = radius
                bounding_capsule_data['depth'] = depth
                bounding_capsule_data['center_point'] = [center[0], center[1], center[2]]
                collider_data.append(bounding_capsule_data)

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

                bounding_capsule_data['parent'] = self.active_obj
                bounding_capsule_data['radius'] = radius
                bounding_capsule_data['depth'] = depth
                bounding_capsule_data['center_point'] = [center[0], center[1], center[2]]
                collider_data = [bounding_capsule_data]

        bpy.context.view_layer.objects.active = self.active_obj
        bpy.ops.object.mode_set(mode='OBJECT')

        for bounding_capsule_data in collider_data:
            global tmp_name

            parent = bounding_capsule_data['parent']
            radius = bounding_capsule_data['radius']
            depth = bounding_capsule_data['depth']
            center = bounding_capsule_data['center_point']

            if self.my_space == 'GLOBAL':
                capsule_data = create_capsule_data(longitudes=self.current_settings_dic['capsule_segments'],
                                                   latitudes=int(self.current_settings_dic['capsule_segments']),
                                                   radius=radius * self.current_settings_dic['width_mult'],
                                                   depth=depth * self.current_settings_dic['height_mult'],
                                                   uv_profile="FIXED")

            else:  # if self.my_space == 'LOCAL':
                capsule_data = create_capsule_data(longitudes=self.current_settings_dic['capsule_segments'],
                                                   latitudes=int(self.current_settings_dic['capsule_segments']),
                                                   radius=radius * self.current_settings_dic['width_mult'],
                                                   depth=depth * self.current_settings_dic['height_mult'],
                                                   uv_profile="FIXED")

            bm = mesh_data_to_bmesh(vs=capsule_data["vs"], vts=capsule_data["vts"], vns=capsule_data["vns"],
                                v_indices=capsule_data["v_indices"], vt_indices=capsule_data["vt_indices"],
                                vn_indices=capsule_data["vn_indices"], )

            mesh_data = bpy.data.meshes.new("Capsule")
            bm.to_mesh(mesh_data)
            bm.free()

            new_collider = bpy.data.objects.new(mesh_data.name, mesh_data)

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
        super().print_generation_time("Capsule Collider", elapsed_time)
        self.report({'INFO'}, f"Capsule Collider: {float(elapsed_time)}")

        return {'RUNNING_MODAL'}
