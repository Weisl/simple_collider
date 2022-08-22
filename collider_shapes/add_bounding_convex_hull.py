import bmesh
import bpy
import numpy as np
from bpy.types import Operator

from .add_bounding_primitive import OBJECT_OT_add_bounding_object


class OBJECT_OT_add_convex_hull(OBJECT_OT_add_bounding_object, Operator):
    """Create convex bounding collisions based on the selection"""
    bl_idname = "mesh.add_bounding_convex_hull"
    bl_label = "Add Convex Hull"
    bl_description = 'Create convex bounding collisions based on the selection'

    def __init__(self):
        super().__init__()
        self.use_decimation = True
        self.use_modifier_stack = True

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

        scene = context.scene
        self.shape_suffix= self.prefs.convex_shape_identifier

        # List for storing dictionaries of data used to generate the collision meshes
        collider_data = []
        verts_co = []

        # Duplicate original meshes to convert to collider
        for obj in self.selected_objects:
            # skip if invalid object
            if obj is None:
                continue

            # skip non Mesh objects like lamps, curves etc.
            if obj.type != "MESH":
                continue

            convex_collision_data = {}

            if self.obj_mode == "EDIT":
                used_vertices = self.get_vertices_Edit(obj, use_modifiers=self.my_use_modifier_stack)

            else:  # self.obj_mode  == "OBJECT":
                used_vertices = self.get_vertices_Object(obj, use_modifiers=self.my_use_modifier_stack)

            if used_vertices == None:  # Skip object if there is no Mesh data to create the collider
                continue

            if self.creation_mode[self.creation_mode_idx] == 'INDIVIDUAL':
                # update mesh when changing selection in edit mode etc.
                obj.update_from_editmode()

                # duplicate object
                convex_collision_data['parent'] = obj

                verts_loc = [v.co for v in used_vertices]
                convex_collision_data['verts_loc'] = verts_loc

                collider_data.append(convex_collision_data)

            else:  # if self.creation_mode[self.creation_mode_idx] == 'SELECTION':
                # get list of all vertex coordinates in global space
                ws_vtx_co = self.get_point_positions(obj, 'GLOBAL', used_vertices)
                verts_co = verts_co + ws_vtx_co

        if self.creation_mode[self.creation_mode_idx] == 'SELECTION':
            convex_collision_data = {}
            convex_collision_data['parent'] = self.active_obj
            convex_collision_data['verts_loc'] = verts_co
            collider_data = [convex_collision_data]

        bpy.ops.object.mode_set(mode='OBJECT')

        for convex_collision_data in collider_data:
            # get data from dictionary
            parent = convex_collision_data['parent']
            verts_loc = convex_collision_data['verts_loc']

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

            new_collider = bpy.data.objects.new('asd', me)
            context.scene.collection.objects.link(new_collider)

            new_collider.parent = parent

            if self.creation_mode[self.creation_mode_idx] == 'SELECTION':
                identityMatrix = np.identity(4)
                new_collider.matrix_world = identityMatrix

            # save collision objects to delete when canceling the operation
            self.new_colliders_list.append(new_collider)
            collections = parent.users_collection
            self.primitive_postprocessing(context, new_collider, collections)

            parent_name = parent.name
            new_collider.name = super().collider_name(basename=parent_name)

        # Initial state has to be restored for the modal operator to work. If not, the result will break once changing the parameters
        super().reset_to_initial_state(context)
        super().print_generation_time("Convex Collider")

        return {'RUNNING_MODAL'}
