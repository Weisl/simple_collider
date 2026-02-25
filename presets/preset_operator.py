import bpy
from .presets_data import presets
from .. import __package__ as base_package
import os
from ..properties.constants import PRESETFOLDER


def simple_collider_presets_folder():
    """
    Ensure the existence of the presets folder for the addon and return its path.

    Returns:
        str: The path to the collider presets directory.
    """
    # Make sure there is a directory for presets
    simple_collider_presets = PRESETFOLDER
    simple_collider_presets_preset_directory = os.path.join(bpy.utils.user_resource('SCRIPTS'), "presets", simple_collider_presets)
    simple_collider_presets_preset_paths = bpy.utils.preset_paths(simple_collider_presets)

    if (simple_collider_presets_preset_directory not in simple_collider_presets_preset_paths) and (
            not os.path.exists(simple_collider_presets_preset_directory)):
        os.makedirs(simple_collider_presets_preset_directory)

    return simple_collider_presets_preset_directory



class SetSimpleColliderPreferencesOperator(bpy.types.Operator):
    """
    Operator to set the preferences for the 'simple_collider' addon based on a selected preset.
    """
    bl_idname = "object.set_simple_collider_prefs"
    bl_label = "Set Simple Collider Preferences"
    preset_name: bpy.props.StringProperty()

    def execute(self, context):
        prefs = bpy.context.preferences.addons[base_package].preferences
        preset = presets[self.preset_name]

        for key, value in preset.items():
            setattr(prefs, key, value)

        return {'FINISHED'}


def get_py_files(self=None, context=None, folder=None):
    """Retrieve all .py files from the specified folder."""
    if folder is None:
        # Fallback to the preset folder logic
        preset_path = None
        if self is not None:  # Check if self is provided and has a preset_path attribute
            preset_path = getattr(self, 'preset_path', None)

        if not preset_path:  # If preset_path is still None, use a fallback
            preset_path = bpy.context.preferences.addons[base_package].preferences.preset_path

        folder = preset_path

    if not folder or not os.path.isdir(folder):
        # print(f"[DEBUG] Invalid folder: {folder}")
        return [("NONE", "Create Presets",
                 "Create export presets export in Blender's default export window before assigning them in Simple Export.")]

    try:
        files = [
            (os.path.join(folder, f), f, "")
            for f in os.listdir(folder)
            if f.endswith(".py")
        ]
        # print(f"[DEBUG] Files found in {folder}: {files}")
        return files if files else [
            ("NONE", "No Files", "Create presets export in the default export windows before assigning them.")]
    except Exception as e:
        # print(f"[DEBUG ERROR] Error reading files in {folder}: {e}")
        return [("NONE", "Error", str(e))]
