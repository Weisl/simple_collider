import bpy

from . import keymap
from . import naming_preset
from . import preferences
from . import properties
from .properties import ColliderTools_Properties
from .keymap import add_hotkey, remove_hotkey
from .preferences import update_panel_category

# keymap needs to be registered before the preferences UI
classes = (
    properties.ColliderTools_Properties,
    naming_preset.COLLISION_preset,
    keymap.COLLISION_OT_add_hotkey_renaming,
    preferences.CollisionAddonPrefs,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    add_hotkey()
    update_panel_category(None, bpy.context)

    # Pointer Properties have to be initialized after classes
    scene = bpy.types.Scene
    scene.collider_tools = bpy.props.PointerProperty(type=ColliderTools_Properties)


def unregister():
    from bpy.utils import unregister_class

    remove_hotkey()

    for cls in reversed(classes):
        unregister_class(cls)
