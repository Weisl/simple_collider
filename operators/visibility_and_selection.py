import bpy

# Enum property.
mode_items = [
    ("ALL", "all", "Show/Hide all collisions", 1),
    ("SIMPLE_COMPLEX", "simple_and_complex", "Show/Hide all simple-complex collisions", 2),
    ("SIMPLE", "simple", "Show/Hide all simple collisions", 4),
    ("COMPLEX", "complex", "Show/Hide all complex collisions", 8),
]


class COLLISION_OT_Visibility(bpy.types.Operator):
    """Hide/Show collision objects"""
    bl_idname = "object.hide_collisions"
    bl_label = "Hide Collision Meshes"
    bl_description = 'Hide/Show collision objects'

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
    """Select/Deselect collision objects"""
    bl_idname = "object.select_collisions"
    bl_label = "Select Collision Meshes"
    bl_description = 'Select/Deselect collision objects'

    select: bpy.props.BoolProperty(
        name='Select/Un-Select',
        default=True
    )

    mode: bpy.props.EnumProperty(items=mode_items,
                                 name='Hide Mode',
                                 default='ALL'
                                 )

    def execute(self, context):
        scene = context.scene

        if self.select:
            for ob in bpy.context.view_layer.objects:
                if self.mode == 'ALL':
                    if ob.get('isCollider') == True:
                        ob.select_set(self.select)
                    else:
                        ob.select_set(not self.select)

                else:  # if self.mode == 'SIMPLE' or self.mode == 'COMPLEX'
                    if ob.get('isCollider') and ob.get('collider_type') == self.mode:
                        ob.select_set(self.select)
                    else:
                        ob.select_set(not self.select)

        else: # self.select = False
            for ob in bpy.context.view_layer.objects:
                if self.mode == 'ALL':
                    if ob.get('isCollider') == True:
                        ob.select_set(self.select)
                else:  # if self.mode == 'SIMPLE' or self.mode == 'COMPLEX'
                    if ob.get('isCollider') and ob.get('collider_type') == self.mode:
                        ob.select_set(self.select)

        return {'FINISHED'}
