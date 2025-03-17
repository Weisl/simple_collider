import bmesh
import bpy
from bpy.types import Operator

from .add_bounding_primitive import OBJECT_OT_add_bounding_object


class OBJECT_OT_add_convex_hull(OBJECT_OT_add_bounding_object, Operator):
    """Create convex bounding collisions based on the selection"""
    bl_idname = "mesh.add_bounding_convex_hull"
    bl_label = "Add Convex Hull"
    bl_description = 'Create convex colliders based on the selection'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_decimation = True
        self.use_geo_nodes_hull = True
        self.use_modifier_stack = True
        self.shape = 'convex_shape'
        self.initial_shape = 'convex_shape'
        self.use_recenter_origin = True

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
        if event.type == 'P' and event.value == 'RELEASE':
            self.my_use_modifier_stack = not self.my_use_modifier_stack
            self.execute(context)

        return {'RUNNING_MODAL'}

    def execute(self, context):
        # CLEANUP
        super().execute(context)

        # List for storing dictionaries of data used to generate the collision meshes
        collider_data = []
        verts_co = []

        objs = self.get_pre_processed_mesh_objs(context, default_world_spc=True)

        for base_ob, obj in objs:

            convex_collision_data = {}

            if self.obj_mode == "EDIT" and base_ob.type == 'MESH' and self.active_obj.type == 'MESH' and not self.use_loose_mesh:
                used_vertices = self.get_edit_mode_vertices_local_space(obj, use_modifiers=self.my_use_modifier_stack)

            else:  # self.obj_mode  == "OBJECT" or self.use_loose_mesh:
                used_vertices = self.get_object_mode_vertices_local_space(obj, use_modifiers=self.my_use_modifier_stack)

            if used_vertices is None:  # Skip object if there is no Mesh data to create the collider
                continue

            ws_vtx_co = self.get_vertex_coordinates(obj, 'GLOBAL', used_vertices)

            creation_mode = self.creation_mode[self.creation_mode_idx] if self.obj_mode == 'OBJECT' else \
                self.creation_mode_edit[self.creation_mode_idx]


            if creation_mode in ['INDIVIDUAL'] or self.use_loose_mesh:

                # duplicate object
                convex_collision_data['parent'] = base_ob
                convex_collision_data['verts_loc'] = ws_vtx_co

                collider_data.append(convex_collision_data)

            else:  # if self.creation_mode[self.creation_mode_idx] == 'SELECTION':
                # get list of all vertex coordinates in global space

                verts_co = verts_co + ws_vtx_co

                convex_collision_data = {}
                convex_collision_data['parent'] = self.active_obj
                convex_collision_data['verts_loc'] = verts_co
                collider_data = [convex_collision_data]


        bpy.context.view_layer.objects.active = self.active_obj
        bpy.ops.object.mode_set(mode='OBJECT')

        for convex_collision_data in collider_data:
            # get data from dictionary
            parent = convex_collision_data['parent']
            verts_loc = convex_collision_data['verts_loc']

            if self.prefs.debug:
                self.create_debug_object_from_verts(context, verts_loc)

            bm = bmesh.new()
            for v in verts_loc:
                bm.verts.new(v)  # add a new vert

            ch = bmesh.ops.convex_hull(bm, input=bm.verts)

            bmesh.ops.delete(
                bm,
                geom=ch["geom_unused"],
                context='VERTS',
            )

            me = bpy.data.meshes.new("mesh")
            bm.to_mesh(me)
            bm.free()

            new_collider = bpy.data.objects.new('colliders', me)
            context.scene.collection.objects.link(new_collider)

            self.custom_set_parent(context, parent, new_collider)

            # save collision objects to delete when canceling the operation
            self.new_colliders_list.append(new_collider)
            collections = parent.users_collection
            self.primitive_postprocessing(context, new_collider, collections)
            super().set_collider_name(new_collider, parent.name)

        # Merge all collider objects
        if self.join_primitives:
            super().join_primitives(context)

        # Initial state has to be restored for the modal operator to work. If not, the result will break once changing the parameters
        super().reset_to_initial_state(context)
        elapsed_time = self.get_time_elapsed()
        super().print_generation_time("Convex Collider", elapsed_time)
        self.report({'INFO'}, f"Convex Collider: {float(elapsed_time)}")

        return {'RUNNING_MODAL'}
