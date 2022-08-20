import bpy

from .visibility_selection_deletion import mode_items


def get_groups_identifier(groups_identifier):
    prefs = bpy.context.preferences.addons[__package__.split('.')[0]].preferences
    identifier = ''

    if groups_identifier == 'ALL_COLLIDER':
        identifier = ''
    elif groups_identifier == 'OBJECTS':
        identifier = ''
    if groups_identifier == 'USER_01':
        identifier = prefs.user_group_01
    elif groups_identifier == 'USER_02':
        identifier = prefs.user_group_02
    elif groups_identifier == 'USER_03':
        identifier = prefs.user_group_03

    return identifier


def get_groups_name(groups_identifier):
    prefs = bpy.context.preferences.addons[__package__.split('.')[0]].preferences
    name = ''

    if groups_identifier == 'ALL_COLLIDER':
        name = 'All Colliders'
    elif groups_identifier == 'OBJECTS':
        name = 'Objects'
    elif groups_identifier == 'USER_01':
        name = prefs.user_group_01_name
    elif groups_identifier == 'USER_02':
        name = prefs.user_group_02_name
    elif groups_identifier == 'USER_03':
        name = prefs.user_group_03_name

    return name


def set_groups_object_color(obj, groups_identifier):
    obj.color = get_groups_color(groups_identifier)


def get_groups_color(groups_identifier):
    prefs = bpy.context.preferences.addons[__package__.split('.')[0]].preferences
    color = [1.0, 1.0, 1.0, 1.0]

    if groups_identifier == 'USER_01':
        color = prefs.user_group_01_color
    elif groups_identifier == 'USER_02':
        color = prefs.user_group_02_color
    elif groups_identifier == 'USER_03':
        color = prefs.user_group_03_color

    return color


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
                set_groups_object_color(obj, self.mode)
                obj['collider_type'] = self.mode

        return {'FINISHED'}
