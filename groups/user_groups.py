import bpy
from .. import __package__ as base_package

default_groups_enum = [
    ('ALL_COLLIDER', "Colliders", "Show/Hide all objects that are colliders.", '', 1),
    ('OBJECTS', "Non Colliders", "Show/Hide all objects that are not colliders.", '', 2),
    ('USER_01', "User Group 01", "Show/Hide all objects that are part of User Group 01", '', 4),
    ('USER_02', "User Group 02", "Show/Hide all objects that are part of User Group 02", '', 8),
    ('USER_03', "User Group 03", "Show/Hide all objects that are part of User Group 03", '', 16)]

default_shape = 'box_shape'
default_group = 'USER_01'


def set_default_group_values():
    from ..groups.user_groups import get_groups_identifier, get_groups_color, get_groups_name

    bpy.context.scene.collider_tools.visibility_toggle_all.mode = 'ALL_COLLIDER'
    bpy.context.scene.collider_tools.visibility_toggle_obj.mode = 'OBJECTS'

    bpy.context.scene.collider_tools.visibility_toggle_user_group_01.mode = 'USER_01'
    bpy.context.scene.collider_tools.visibility_toggle_user_group_01.name = get_groups_name('USER_01')
    bpy.context.scene.collider_tools.visibility_toggle_user_group_01.identifier = get_groups_identifier('USER_01')
    bpy.context.scene.collider_tools.visibility_toggle_user_group_01.color = get_groups_color('USER_01')

    bpy.context.scene.collider_tools.visibility_toggle_user_group_02.mode = 'USER_02'
    bpy.context.scene.collider_tools.visibility_toggle_user_group_02.name = get_groups_name('USER_02')
    bpy.context.scene.collider_tools.visibility_toggle_user_group_02.identifier = get_groups_identifier('USER_02')
    bpy.context.scene.collider_tools.visibility_toggle_user_group_02.color = get_groups_color('USER_02')

    bpy.context.scene.collider_tools.visibility_toggle_user_group_03.mode = 'USER_03'
    bpy.context.scene.collider_tools.visibility_toggle_user_group_03.name = get_groups_name('USER_03')
    bpy.context.scene.collider_tools.visibility_toggle_user_group_03.identifier = get_groups_identifier('USER_03')
    bpy.context.scene.collider_tools.visibility_toggle_user_group_03.color = get_groups_color('USER_03')


def update_hide(self, context):
    for ob in bpy.context.view_layer.objects:
        if self.mode == 'ALL_COLLIDER':
            if ob.get('isCollider') == True:
                ob.hide_viewport = self.hide
        elif self.mode == 'OBJECTS':
            if ob.get('isCollider') == None:
                ob.hide_viewport = self.hide
        else:  # if self.mode == 'USER_02' or self.mode == 'USER_03'
            if ob.get('isCollider') and ob.get('collider_group') == self.mode:
                ob.hide_viewport = self.hide


def update_selected(self, context):
    print("self.select = " + str(self.selected))
    for ob in bpy.data.objects:
        if self.selected == True:
            ob.select_set(False)
        else:  # self.selected == False
            if self.mode == 'ALL_COLLIDER':
                if ob.get('isCollider'):
                    ob.select_set(not self.selected)

            elif self.mode == 'OBJECTS':
                if not ob.get('isCollider'):
                    ob.select_set(not self.selected)

            else:  # if self.mode == 'USER_02' or self.mode == 'USER_03'
                if ob.get('isCollider') and ob.get('collider_group') == self.mode:
                    ob.select_set(not self.selected)


def get_groups_color(groups_identifier):
    prefs = bpy.context.preferences.addons[base_package].preferences
    color = [1.0, 1.0, 1.0]

    if groups_identifier == 'USER_01':
        color = prefs.user_group_01_color
    elif groups_identifier == 'USER_02':
        color = prefs.user_group_02_color
    elif groups_identifier == 'USER_03':
        color = prefs.user_group_03_color

    return color


class ColliderGroup(bpy.types.PropertyGroup):

    def get_groups_enum(self):
        '''Set name and description according to type'''
        for group in default_groups_enum:
            if group[4] == self["mode"]:
                # self.identifier = get_complexity_suffix(group[0])
                self.name = get_groups_name(group[0])
                self.identifier = get_groups_identifier(group[0])
                self.icon = group[3]
                self.color = get_groups_color(group[0])
        return self["mode"]

    def set_groups_enum(self, val):
        self["mode"] = val
        # ColliderGroup.mode.val = str(val)

    mode: bpy.props.EnumProperty(name="Group",
                                 items=default_groups_enum,
                                 description="",
                                 default='ALL_COLLIDER',
                                 get=get_groups_enum,
                                 set=set_groups_enum
                                 )

    name: bpy.props.StringProperty()
    identifier: bpy.props.StringProperty()
    icon: bpy.props.StringProperty()

    color: bpy.props.FloatVectorProperty(name="Color",
                                         subtype='COLOR',
                                         options={'TEXTEDIT_UPDATE'},
                                         size=3,
                                         default=[0.0, 0.0, 0.0])

    hide: bpy.props.BoolProperty(default=False, update=update_hide,
                                 name='Disable in Viewport',
                                 description="Show/Hide all objects that are not colliders.")

    selected: bpy.props.BoolProperty(default=False, name="Select/Deselect", update=update_selected)

    show_icon: bpy.props.StringProperty(default='RESTRICT_VIEW_OFF')
    hide_icon: bpy.props.StringProperty(default='RESTRICT_VIEW_ON')

    show_text: bpy.props.StringProperty(default='')
    hide_text: bpy.props.StringProperty(default='')

    selected_icon: bpy.props.StringProperty(default='RESTRICT_SELECT_OFF')
    deselected_icon: bpy.props.StringProperty(default='RESTRICT_SELECT_ON')
    selected_text: bpy.props.StringProperty(default='')
    deselected_text: bpy.props.StringProperty(default='')

    delete_icon: bpy.props.StringProperty(default='TRASH')
    delete_text: bpy.props.StringProperty(default='')


def get_groups_identifier(groups_identifier):
    prefs = bpy.context.preferences.addons[base_package].preferences
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
    prefs = bpy.context.preferences.addons[base_package].preferences
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


def set_object_color(obj, color):
    obj.color = color


class COLLISION_OT_assign_user_group(bpy.types.Operator):
    """Select/Deselect collision objects"""
    bl_idname = "object.assign_user_group"
    bl_label = "Assign User Group"
    bl_description = 'Assign User Group to collider'
    bl_options = {"REGISTER", "UNDO"}

    mode: bpy.props.EnumProperty(items=default_groups_enum,
                                 name='Mode',
                                 default='ALL_COLLIDER'
                                 )

    @classmethod
    def poll(cls, context):
        count = 0
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                count += 1
        return count > 0

    def execute(self, context):
        prefs = context.preferences.addons[base_package].preferences

        count = 0
        for obj in context.selected_objects.copy():
            # skip if invalid object
            if obj is None or obj.type != "MESH" or not obj.get('isCollider'):
                continue
            count += 1

            obj['collider_group'] = self.mode
            col = get_groups_color(self.mode)
            alpha = prefs.user_groups_alpha
            set_object_color(obj, (col[0], col[1], col[2], alpha))

            if prefs.replace_name:
                basename = prefs.obj_basename
            elif obj.parent:
                basename = obj.parent.name
            else:
                basename = obj.name

            # get collider shape and group and set to default there is no previous data
            shape_identifier = default_shape if obj.get('collider_shape') is None else obj.get('collider_shape')
            user_group = default_group if obj.get('collider_group') is None else obj.get('collider_group')

            from ..collider_shapes.add_bounding_primitive import OBJECT_OT_add_bounding_object

            new_name = OBJECT_OT_add_bounding_object.class_collider_name(shape_identifier=shape_identifier,
                                                                         user_group=get_groups_identifier(user_group),
                                                                         basename=basename)
            data_name = OBJECT_OT_add_bounding_object.set_data_name(obj, new_name, "_data")

            obj.name = new_name
            obj.data.name = data_name

        if count == 0:
            self.report({'WARNING'}, "No collider found to change the user group.")
            return {'CANCELLED'}

        return {'FINISHED'}
