import bpy
from bpy.types import Operator
from mathutils import Matrix, Vector
from . import capsule_generation as Capsule
from math import radians

from .utilities import get_sca_matrix, get_rot_matrix, get_loc_matrix
from .add_bounding_primitive import OBJECT_OT_add_bounding_object

tmp_name = 'capsule_collider'

class OBJECT_OT_add_bounding_capsule(OBJECT_OT_add_bounding_object, Operator):
    """Create bounding capsule collider based on the selection"""
    bl_idname = "mesh.add_bounding_capsule"
    bl_label = "Add Capsule"
    bl_description = 'Create bounding capsule colliders based on the selection'

    def __init__(self):
        super().__init__()
        self.use_space = True
        self.use_modifier_stack = True
        self.use_global_local_switches = True
        self.use_capsule_axis = True
        self.use_capsule_segments = True
        self.shape = 'capsule_shape'


    def invoke(self, context, event):
        super().invoke(context, event)
        return {'RUNNING_MODAL'}

    def set_modal_capsule_segments_active(self, context):
        self.capsule_segments_active = not self.capsule_segments_active
        self.displace_active = False
        self.opacity_active = False
        self.decimate_active = False
        self.cylinder_segments_active = False
        self.execute(context)


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
            self.set_modal_capsule_segments_active(context)

        # change bounding object settings
        if event.type == 'P' and event.value == 'RELEASE':
            self.my_use_modifier_stack = not self.my_use_modifier_stack
            self.execute(context)

        # define cylinder axis
        elif event.type == 'X' or event.type == 'Y' or event.type == 'Z' and event.value == 'RELEASE':
            self.cylinder_axis = event.type
            self.execute(context)

        return {'RUNNING_MODAL'}

    def execute(self, context):
        super().execute(context)

        # List for storing dictionaries of data used to generate the collision meshes
        collider_data = []
        verts_co = []

        # Create the bounding geometry, depending on edit or object mode.
        for obj in self.selected_objects:

            # skip if invalid object
            if not self.is_valid_object(obj):
                continue

            context.view_layer.objects.active = obj
            bounding_capsule_data = {}

            if self.obj_mode == "EDIT":
                used_vertices = self.get_vertices_Edit(obj, use_modifiers=self.my_use_modifier_stack)

            else:  # self.obj_mode  == "OBJECT":
                used_vertices = self.get_vertices_Object(obj, use_modifiers=self.my_use_modifier_stack)

            if used_vertices is None:  # Skip object if there is no Mesh data to create the collider
                continue

            # Save base object coordinates
            matrix_WS = obj.matrix_world
            loc, rot, sca = matrix_WS.decompose()


            if self.creation_mode[self.creation_mode_idx] == 'INDIVIDUAL':
                # used_vertices uses local space.
                coordinates = []

                for vertex in used_vertices:

                    # Ignore Scale
                    if self.my_space == 'LOCAL':
                        v = vertex.co @ get_sca_matrix(sca)

                    else:
                        # Scale has to be applied before location
                        v = vertex.co @ get_sca_matrix(sca) @ get_loc_matrix(loc) @ get_rot_matrix(rot)

                    if self.cylinder_axis == 'X':
                        coordinates.append([v.y, v.z, v.x])
                    elif self.cylinder_axis == 'Y':
                        coordinates.append([v.x, v.z, v.y])
                    elif self.cylinder_axis == 'Z':
                        coordinates.append([v.x, v.y, v.z])

                center = sum((Vector(matrix_WS @ Vector(v)) for v in coordinates), Vector()) / len(used_vertices)


                # store data needed to generate a bounding box in a dictionary
                bounding_capsule_data['parent'] = obj
                bounding_capsule_data['verts_loc'] = coordinates
                bounding_capsule_data['center_point'] = [center[0], center[1], center[2]]
                collider_data.append(bounding_capsule_data)
            else:  # if self.creation_mode[self.creation_mode_idx] == 'SELECTION':

                # get list of all vertex coordinates in global space
                ws_vtx_co = self.get_point_positions(obj, 'GLOBAL', used_vertices)
                verts_co = verts_co + ws_vtx_co

        if self.creation_mode[self.creation_mode_idx] == 'SELECTION':

            # Scale has to be applied before location
            center = sum((Vector(v_co) for v_co in verts_co), Vector()) / len(verts_co)

            # store data needed to generate a bounding box in a dictionary
            bounding_capsule_data['parent'] = self.active_obj
            bounding_capsule_data['verts_loc'] = verts_co
            bounding_capsule_data['center_point'] = [center[0], center[1], center[2]]
            collider_data.append(bounding_capsule_data)

        bpy.ops.object.mode_set(mode='OBJECT')

        for bounding_capsule_data in collider_data:
            # get data from dictionary
            parent = bounding_capsule_data['parent']
            verts_loc = bounding_capsule_data['verts_loc']
            center = bounding_capsule_data['center_point']

            # Calculate the radius and height of the bounding capsule
            radius, height = Capsule.calculate_radius_height(verts_loc)
            #height, radius = calculate_bounding_capsule(verts_loc)
            print("Optimal bounding capsule height:", height)
            print("Optimal bounding capsule radius:", radius)
            data = Capsule.create_capsule(longitudes=self.current_settings_dic['capsule_segments'], latitudes=int(self.current_settings_dic['capsule_segments']), radius=radius, depth=height, uv_profile="FIXED")
            bm = Capsule.mesh_data_to_bmesh(
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
            new_collider.location = center
            #context.scene.collection.objects.link(new_collider)

            if  self.my_space == 'LOCAL' and self.creation_mode[self.creation_mode_idx] == 'INDIVIDUAL':
                # Align the bounding capsule with the original object's rotation
                new_collider.rotation_euler = parent.rotation_euler

            if self.cylinder_axis == 'X':
                new_collider.rotation_euler.rotate_axis("Y", radians(90))
            elif self.cylinder_axis == 'Y':
                new_collider.rotation_euler.rotate_axis("X", radians(90))

            # save collision objects to delete when canceling the operation
            self.new_colliders_list.append(new_collider)
            collections = parent.users_collection
            self.primitive_postprocessing(context, new_collider, collections)

            parent_name = parent.name
            super().set_collider_name(new_collider, parent_name)
            self.custom_set_parent(context, parent, new_collider)

        # Initial state has to be restored for the modal operator to work. If not, the result will break once changing the parameters
        super().reset_to_initial_state(context)
        elapsed_time = self.get_time_elapsed()
        super().print_generation_time("Capsule Collider", elapsed_time)
        self.report({'INFO'}, f"Capsule Collider: {float(elapsed_time)}")

        return {'RUNNING_MODAL'}

