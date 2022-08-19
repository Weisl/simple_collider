import bpy

from .visibility_selection_deletion import mode_items


def get_complexity_suffix(complexity_identifier):
    suffix = ''
    print('complexity_identifier ' + str(complexity_identifier))
    prefs = bpy.context.preferences.addons[__package__.split('.')[0]].preferences
    if complexity_identifier == 'ALL_COLLIDER':
        suffix = ''
    elif complexity_identifier == 'OBJECTS':
        suffix = ''
    if complexity_identifier == 'USER_01':
        suffix = prefs.user_group_01
    elif complexity_identifier == 'USER_02':
        suffix = prefs.user_group_02
    elif complexity_identifier == 'USER_03':
        suffix = prefs.user_group_03
    return suffix


def get_complexity_name(complexity_identifier):
    name = ''
    print('complexity_identifier ' + str(complexity_identifier))
    prefs = bpy.context.preferences.addons[__package__.split('.')[0]].preferences
    if complexity_identifier == 'ALL_COLLIDER':
        name = 'All Colliders'
    elif complexity_identifier == 'OBJECTS':
        name = 'Objects'
    elif complexity_identifier == 'USER_01':
        name = prefs.user_group_01_name
    elif complexity_identifier == 'USER_02':
        name = prefs.user_group_02_name
    elif complexity_identifier == 'USER_03':
        name = prefs.user_group_03_name
    return name


def set_object_color(obj, complexity_identifier):
    prefs = bpy.context.preferences.addons[__package__.split('.')[0]].preferences
    if complexity_identifier == 'USER_01':
        obj.color = prefs.user_group_01_color
    elif complexity_identifier == 'USER_02':
        obj.color = prefs.user_group_02_color
    elif complexity_identifier == 'USER_03':
        obj.color = prefs.user_group_03_color


def get_group_color(complexity_identifier):
    prefs = bpy.context.preferences.addons[__package__.split('.')[0]].preferences
    if complexity_identifier == 'USER_01':
        return prefs.user_group_01_color
    elif complexity_identifier == 'USER_02':
        return prefs.user_group_02_color
    elif complexity_identifier == 'USER_03':
        return prefs.user_group_03_color


class COLLISION_OT_assign_user_group(bpy.types.Operator):
    """Select/Deselect collision objects"""
    bl_idname = "object.assign_user_group"
    bl_label = "Assign User Group"
    bl_description = 'Assign User Group to collider'
    bl_options = {"REGISTER", "UNDO"}

    mode: bpy.props.EnumProperty(items=mode_items,
                                 name='Mode',
                                 default='ALL_COLLIDER'
                                 )

    def execute(self, context):
        for obj in context.selected_objects.copy():
            if obj.type == 'MESH':
                set_object_color(obj, self.mode)
                obj['collider_type'] = self.mode

        return {'FINISHED'}


