import bpy

from . import user_groups

default_groups_enum = [('ALL_COLLIDER', "Colliders", "Show/Hide all objects that are colliders.", '', 1),
                       ('OBJECTS', "Non Colliders", "Show/Hide all objects that are not colliders.", '', 2),
                       ('USER_01', "User Group 01",
                        "Show/Hide all objects that are part of User Group 01", '', 4),
                       ('USER_02', "User Group 02", "Show/Hide all objects that are part of User Group 02", '', 8),
                       ('USER_03', "User Group 03", "Show/Hide all objects that are part of User Group 03", '', 16)]


def update_hide(self, context):
    print("self.hide = " + str(self.hide))
    for ob in bpy.context.view_layer.objects:
        if self.mode == 'ALL_COLLIDER':
            if ob.get('isCollider') == True:
                ob.hide_viewport = self.hide
        elif self.mode == 'OBJECTS':
            print('0')
            if ob.get('isCollider') == None:
                print('1')
                ob.hide_viewport = self.hide
        else:  # if self.mode == 'USER_02' or self.mode == 'USER_03'
            if ob.get('isCollider') and ob.get('collider_type') == self.mode:
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
                if ob.get('isCollider') and ob.get('collider_type') == self.mode:
                    ob.select_set(not self.selected)


class ColliderGroup(bpy.types.PropertyGroup):

    def get_groups_enum(self):
        '''Set name and description according to type'''
        for group in default_groups_enum:
            if group[4] == self["mode"]:
                from .user_groups import get_groups_name
                from .user_groups import get_groups_identifier
                from .user_groups import get_groups_color
                # self.identifier = get_complexity_suffix(group[0])
                self.name = get_groups_name(group[0])
                self.identifier = get_groups_identifier(group[0])
                self.icon = group[3]

                color = get_groups_color(group[0])
                self.color = (color[0], color[1], color[2])

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


classes = (
    ColliderGroup,
    user_groups.COLLISION_OT_assign_user_group,
)


def register():
    scene = bpy.types.Scene

    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    # Pointer Properties have to be initialized after classes
    scene.visibility_toggle_all = bpy.props.PointerProperty(type=ColliderGroup)
    scene.visibility_toggle_obj = bpy.props.PointerProperty(type=ColliderGroup)
    scene.visibility_toggle_user_group_01 = bpy.props.PointerProperty(type=ColliderGroup)
    scene.visibility_toggle_user_group_02 = bpy.props.PointerProperty(type=ColliderGroup)
    scene.visibility_toggle_user_group_03 = bpy.props.PointerProperty(type=ColliderGroup)




def unregister():
    scene = bpy.types.Scene

    del scene.visibility_toggle_user_group_03
    del scene.visibility_toggle_user_group_02
    del scene.visibility_toggle_user_group_01
    del scene.visibility_toggle_obj
    del scene.visibility_toggle_all

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
