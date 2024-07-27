import os
import shutil
from pathlib import Path
from .. import __package__ as base_package
from . import properties_panels
from . import popup
from .properties_panels import collider_presets_folder

classes = (
    properties_panels.EXPLORER_OT_open_directory_new,
    properties_panels.PREFERENCES_OT_open_addon,
    properties_panels.BUTTON_OT_auto_convex,
    properties_panels.OBJECT_MT_collision_presets,
    properties_panels.VIEW3D_MT_collision_creation,
    properties_panels.VIEW3D_PT_collision_panel,
    properties_panels.VIEW3D_PT_collision_settings_panel,
    properties_panels.VIEW3D_PT_collision_visibility_panel,
    properties_panels.VIEW3D_PT_collision_material_panel,
    properties_panels.VIEW3D_MT_PIE_template,
    popup.VIEW3D_PT_auto_convex_popup,
)


def get_preset_folder_path():
    path = Path(str(__file__))
    parent = path.parent.parent.parent.absolute()

    collider_presets = str(base_package)
    return os.path.join(parent, collider_presets, "presets")


def initialize_presets():
    my_presets = collider_presets_folder()

    # Get a list of all the files in your bundled presets folder
    my_bundled_presets = get_preset_folder_path()
    print("Preset Path: " + my_bundled_presets)
    print("My Presets: " + my_presets)
    # files = os.listdir(my_bundled_presets)

    # Copy them
    # for f in files:
    #     filepath = os.path.join(my_bundled_presets, f)
    #     shutil.copy2(filepath, my_presets)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    initialize_presets()


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
