import bpy



class COLLISION_OT_Visibility(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.hide_collisions"
    bl_label = "Hide Collision Meshes"

    hide: bpy.props.BoolProperty(
        name='Hide/Unhide',
        default=True
    )

    # @classmethod
    # def poll(cls, context):
    #     return context.active_object is not None

    def execute(self, context):
        scene = context.scene

        # objects = [ob.hide_set(True) for ob in bpy.context.view_layer.objects if ob.get('isCollider')]
        for ob in bpy.context.view_layer.objects:
            if ob.get('isCollider') == True:
                ob.hide_viewport = self.hide

                # hide throws errors :(
                # ob.hide_set = False


        return {'FINISHED'}
