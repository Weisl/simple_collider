import bpy
from . import keymap
from . import preferences
from . import naming_preset
from .keymap import add_hotkey, remove_hotkey


#keymap needs to be registered before the preferences UI
classes = (
    naming_preset.COLLISION_preset,
    naming_preset.OBJECT_MT_collision_presets,

    keymap.COLLISION_OT_add_hotkey_renaming,
    preferences.CollisionAddonPrefs,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    add_hotkey()


def unregister():
    from bpy.utils import unregister_class

    remove_hotkey()

    for cls in reversed(classes):
        unregister_class(cls)
