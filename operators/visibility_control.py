import bpy

# Enum property.
mode_items = [
    ("ALL", "all", "", 1),
    ("SIMPLE", "simple", "", 2),
    ("COMPLEX", "complex", "", 3),
]


class COLLISION_OT_Visibility(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.hide_collisions"
    bl_label = "Hide Collision Meshes"

    hide: bpy.props.BoolProperty(
        name='Hide/Unhide',
        default=True
    )

    mode: bpy.props.EnumProperty(items=mode_items,
                                 name='Hide Mode',
                                 default='ALL'
                                 )

    def execute(self, context):
        scene = context.scene

        # objects = [ob.hide_set(True) for ob in bpy.context.view_layer.objects if ob.get('isCollider')]
        for ob in bpy.context.view_layer.objects:
            if ob.get('isCollider') == True:
                if self.mode == 'ALL':
                    ob.hide_viewport = self.hide
                elif self.mode == 'SIMPLE':
                    if ob.get('simple') == True:
                        ob.hide_viewport = self.hide
                elif self.mode == 'COMPLEX':
                    if ob.get('complex') == True:
                        ob.hide_viewport = self.hide

        return {'FINISHED'}
