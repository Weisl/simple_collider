import bpy
from bpy.types import Operator

from .add_bounding_primitive import OBJECT_OT_add_bounding_object
from ..bmesh_operations.box_creation import verts_faces_to_bbox_collider

tmp_name = 'box_collider'


class OBJECT_OT_add_bounding_box(OBJECT_OT_add_bounding_object, Operator):
    """Create bounding box collisions based on the selection"""
    bl_idname = "mesh.add_bounding_box"
    bl_label = "Add Box"
    bl_description = 'Create bounding box colliders based on the selection'

    def __init__(self):
        super().__init__()
        self.use_space = True
        self.use_modifier_stack = True
        self.use_global_local_switches = True
        self.shape = 'box_shape'
        self.initial_shape = 'box_shape'

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
        if event.type == 'P' and event.value == 'RELEASE':
            self.my_use_modifier_stack = not self.my_use_modifier_stack
            self.execute(context)

        return {'RUNNING_MODAL'}

    def execute(self, context):
        # CLEANUP and INIT
        super().execute(context)

        # List for storing dictionaries of data used to generate the collision meshes
        collider_data = []
        verts_co = []

        objs = self.get_pre_processed_mesh_objs(context, use_local=True, local_world_spc=False, default_world_spc=True)

        for base_ob, obj in objs:

            context.view_layer.objects.active = obj
            bounding_box_data = {}

            # EDIT is only supported for 'MESH' type objects and only if the active object is a 'MESH'
            if self.obj_mode == "EDIT" and base_ob.type == 'MESH' and self.active_obj.type == 'MESH' and not self.use_loose_mesh:
                # Use Mesh uses copies of edit mode meshes
                used_vertices = self.get_edit_mode_vertices_local_space(obj, use_modifiers=self.my_use_modifier_stack)
            else:  # self.obj_mode  == "OBJECT" or self.use_loose_mesh:
                used_vertices = self.get_object_mode_vertices_local_space(obj, use_modifiers=self.my_use_modifier_stack)

            if used_vertices is None:  # Skip object if there is no Mesh data to create the collider
                continue


            creation_mode = self.creation_mode[self.creation_mode_idx] if self.obj_mode == 'OBJECT' else \
                self.creation_mode_edit[self.creation_mode_idx]
            if creation_mode in ['INDIVIDUAL'] or self.use_loose_mesh:

                # used_vertices uses local space.
                co = self.get_vertex_coordinates(obj, self.my_space, used_vertices)
                verts_loc, center_point = self.generate_bounding_box(co)

                # store data needed to generate a bounding box in a dictionary
                bounding_box_data['parent'] = base_ob
                bounding_box_data['mtx_world'] = base_ob.matrix_world.copy()
                bounding_box_data['verts_loc'] = verts_loc
                bounding_box_data['center_point'] = center_point

                collider_data.append(bounding_box_data)

            else:  # if self.creation_mode[self.creation_mode_idx] == 'SELECTION':
                # get list of all vertex coordinates in global space
                ws_vtx_co = self.get_vertex_coordinates(obj, 'GLOBAL', used_vertices)
                verts_co = verts_co + ws_vtx_co
                collider_data = self.selection_bbox_data(verts_co)

        bpy.ops.object.mode_set(mode='OBJECT')

        for bounding_box_data in collider_data:
            # get data from dictionary
            parent = bounding_box_data['parent']
            verts_loc = bounding_box_data['verts_loc']
            center_point = bounding_box_data['center_point']
            mtx_world = bounding_box_data['mtx_world']

            new_collider = verts_faces_to_bbox_collider(self, context, verts_loc)

            if self.my_space == 'LOCAL':
                new_collider.matrix_world = mtx_world
                # align collider with parent
                self.custom_set_parent(context, parent, new_collider)
                self.use_recenter_origin = True


            else:  # self.my_space == 'GLOBAL':
                self.custom_set_parent(context, parent, new_collider)

                self.use_recenter_origin = True
                self.col_center_loc_list.append(center_point)

            # save collision objects to delete when canceling the operation
            self.new_colliders_list.append(new_collider)
            collections = parent.users_collection
            self.primitive_postprocessing(context, new_collider, collections)

            parent_name = parent.name
            super().set_collider_name(new_collider, parent_name)


        # Merge all collider objects
        if self.join_primitives:
            super().join_primitives(context)

        # Initial state has to be restored for the modal operator to work. If not, the result will break once changing the parameters
        super().reset_to_initial_state(context)
        elapsed_time = self.get_time_elapsed()
        super().print_generation_time("Box Collider", elapsed_time)
        self.report({'INFO'}, f"Box Collider: {float(elapsed_time)}")

        return {'RUNNING_MODAL'}

    def selection_bbox_data(self, verts_co):
        if self.my_space == 'LOCAL':
            ws_vtx_co = verts_co
            verts_co = self.transform_vertex_space(ws_vtx_co, self.active_obj)

        bbox_verts, center_point = self.generate_bounding_box(verts_co)
        mtx_world = self.active_obj.matrix_world

        bounding_box_data = {'parent': self.active_obj, 'verts_loc': bbox_verts, 'center_point': center_point,
                             'mtx_world': mtx_world}

        return [bounding_box_data]
