from . import keymap
from . import preferences
from .keymap import add_hotkey, remove_hotkey

classes = (
    preferences.CollisionAddonPrefs,
    keymap.RENAMING_OT_add_hotkey_renaming,
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
