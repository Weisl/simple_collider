import bpy
from bpy.app.handlers import persistent

from . import naming_preset
from . import preferences
from . import keymap

from .preferences import update_panel_category
from ..pyshics_materials.material_functions import set_default_active_mat

classes = (
    naming_preset.COLLISION_preset,
    preferences.BUTTON_OT_change_key,
    preferences.CollisionAddonPrefs,
    keymap.REMOVE_OT_hotkey,
)

@persistent
def _load_handler(dummy):
    set_default_active_mat()

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

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    update_panel_category(None, bpy.context)

    # Pointer Properties have to be initialized after classes

    keymap.add_keymap()
    bpy.app.handlers.load_post.append(_load_handler)

def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    keymap.remove_keymap()
    bpy.app.handlers.load_post.remove(_load_handler)
