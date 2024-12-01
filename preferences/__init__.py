import bpy
from bpy.app.handlers import persistent

from . import keymap
from . import preferences
from .preferences import update_panel_category
from ..groups.user_groups import set_default_group_values
from ..pyshics_materials.material_functions import set_default_active_mat

classes = (
    preferences.BUTTON_OT_change_key,
    preferences.CollisionAddonPrefs,
    keymap.REMOVE_OT_hotkey,
)


@persistent
def _load_handler(dummy):
    """
    Handler function that is called when a new Blender file is loaded.
    This function sets the default active material and default group values.
    """
    set_default_active_mat()
    set_default_group_values()


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    update_panel_category(None, bpy.context)
    keymap.add_keymap()

    # Append the load handler to be executed after loading a Blender file
    bpy.app.handlers.load_post.append(_load_handler)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    keymap.remove_keymap()
    # Remove the load handler
    bpy.app.handlers.load_post.remove(_load_handler)
