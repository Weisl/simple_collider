import bpy


class COLLISION_OT_Visibility(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.hide_collisions"
    bl_label = "Hide Collision Meshes"

    # @classmethod
    # def poll(cls, context):
    #     return context.active_object is not None

    def execute(self, context):
        scene = context.scene

        # objects = [ob.hide_set(True) for ob in bpy.context.view_layer.objects if ob.get('isCollider')]
        for ob in bpy.context.view_layer.objects:
            if ob.get('isCollider'):
                ob.hide_viewport = scene.my_hide

        return {'FINISHED'}
