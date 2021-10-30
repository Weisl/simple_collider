import bpy

# Enum property.
mode_items = [
    ("ALL", "all", "", 1),
    ("SIMPLE", "simple", "", 2),
    ("COMPLEX", "complex", "", 3),
    ("SIMPLE_COMPLEX", "simple_and_complex", "", 4),
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
            if self.mode == 'ALL':
                if ob.get('isCollider') == True:
                    ob.hide_viewport = self.hide
            else:  # if self.mode == 'SIMPLE' or self.mode == 'COMPLEX'
                if ob.get('isCollider') and ob.get('collider_type') == self.mode:
                    ob.hide_viewport = self.hide

        return {'FINISHED'}

class COLLISION_OT_Selection(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.select_collisions"
    bl_label = "Select Collision Meshes"

    invert: bpy.props.BoolProperty(
        name='Hide/Unhide',
        default=True
    )

    mode: bpy.props.EnumProperty(items=mode_items,
                                 name='Hide Mode',
                                 default='ALL'
                                 )

    def execute(self, context):
        scene = context.scene

        select = True
        if self.invert:
            select = False

        for ob in bpy.context.view_layer.objects:
            if self.mode == 'ALL':
                if ob.get('isCollider') == True:
                    ob.select_set(select)
                else:
                    ob.select_set(not select)

            else:  # if self.mode == 'SIMPLE' or self.mode == 'COMPLEX'
                if ob.get('isCollider') and ob.get('collider_type') == self.mode:
                    ob.select_set(select)
                else:
                    ob.select_set(not select)

        return {'FINISHED'}
