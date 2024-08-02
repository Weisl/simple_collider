import bpy
import os

from . import popup
from . import properties_panels
from .properties_panels import collider_presets_folder
from .. import __package__ as base_package
from ..presets.presets_data import presets

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


def set_preferences(preset):
    """
    Set the preferences for the 'collider_tools' addon based on the given preset.

    Args:
        preset (dict): The preset containing preference settings.

    Returns:
        None
    """
    prefs = bpy.context.preferences.addons[base_package].preferences
    for key, value in preset.items():
        setattr(prefs, key, value)


def save_preset(preset_name, preset):
    """
    Save the given preset as a Blender preset.

    Args:
        preset_name (str): The name of the preset.
        preset (dict): The preset containing preference settings.

    Returns:
        None
    """
    user_preset_folder = collider_presets_folder()

    preset_file_path = os.path.join(user_preset_folder, f'{preset_name}.py')

    with open(preset_file_path, 'w') as preset_file:
        preset_file.write(f"import bpy\n\n")
        preset_file.write(f"prefs = bpy.context.preferences.addons['{base_package}'].preferences\n\n")
        for key, value in preset.items():
            if isinstance(value, str):
                preset_file.write(f"prefs.{key} = '{value}'\n")
            else:
                preset_file.write(f"prefs.{key} = {value}\n")
    print(f'Preset created: {preset_name}')

def initialize_presets():
    user_preset_folder = collider_presets_folder()
    print("User Preset Folder: " + user_preset_folder)
    saved_preset_files = os.listdir(user_preset_folder)
    print("Saved User Presets: " + str(saved_preset_files))

    for preset_name, preset in presets.items():
        if preset_name not in saved_preset_files:
            save_preset(preset_name, preset)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    initialize_presets()


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
