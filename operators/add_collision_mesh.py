import bmesh
import bpy
from bpy.types import Operator

from .add_bounding_primitive import OBJECT_OT_add_bounding_object


def add_modifierstack(self, obj):
    modifier = obj.modifiers.new(name="Collider_displace", type='DISPLACE')
    modifier.strength = 0.0

    modifier = obj.modifiers.new(name="Collider_remesh", type='REMESH')
    modifier.voxel_size = 0.2
    modifier.use_smooth_shade = True

    mod = obj.modifiers.new(name="Collider_decimate", type='DECIMATE')
    mod.ratio = 0.1
    self.face_count = mod.face_count


class OBJECT_OT_add_mesh_collision(OBJECT_OT_add_bounding_object, Operator):
    """Create a new bounding box object"""
    bl_idname = "mesh.add_mesh_collision"
    bl_label = "Add Mesh Collision"

    def invoke(self, context, event):
        super().invoke(context, event)
        self.face_count = 0
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        status = super().modal(context, event)
        if status == {'FINISHED'}:
            return {'FINISHED'}
        if status == {'CANCELLED'}:
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def execute(self, context):
        self.remove_objects(self.new_colliders_list)
        self.new_colliders_list = []

        # reset previously stored displace modifiers when creating a new object
        self.displace_modifiers = []

        # Add the active object to selection if it's not selected. This fixes the rare case when the active Edit mode object is not selected in Object mode.
        if context.object not in self.selected_objects:
            self.selected_objects.append(context.object)

        old_objs = set(context.scene.objects)

        for i, obj in enumerate(self.selected_objects):

            # skip if invalid object
            if obj is None:
                continue

            # skip non Mesh objects like lamps, curves etc.
            if obj.type != "MESH":
                continue

            context.view_layer.objects.active = obj
            collections = obj.users_collection

            if obj.mode == "EDIT":
                bpy.ops.mesh.duplicate()
                bpy.ops.mesh.separate(type='SELECTED')

            else:  # mode == "OBJECT":
                bpy.ops.object.mode_set(mode='EDIT')

                # Get a BMesh representation
                me = obj.data
                bm = bmesh.from_edit_mesh(me)

                # select all vertices
                self.get_vertices(bm, preselect_all=True)

                bpy.ops.mesh.duplicate()
                bpy.ops.mesh.separate(type='SELECTED')

                pass

            bpy.ops.object.mode_set(mode='OBJECT')
            new_collider = context.scene.objects[-1]
            new_collider.name = obj.name + self.name_suffix + "_" + str(i)
            add_modifierstack(self, new_collider, )
            # create collision meshes
            self.custom_set_parent(context, obj, new_collider)

            # save collision objects to delete when canceling the operation
            # self.previous_objects.append(new_collider)
            self.primitive_postprocessing(context, new_collider, self.physics_material_name)
            self.add_to_collections(new_collider, collections)

            # infomessage = 'Generated collisions %d/%d' % (i, obj_amount)
            # self.report({'INFO'}, infomessage)

        self.new_colliders_list = set(context.scene.objects) - old_objs

        return {'RUNNING_MODAL'}
