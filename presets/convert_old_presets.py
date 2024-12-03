import os
from bpy.types import Operator
from .. import __package__ as base_package
from .naming_preset import COLLISION_preset
from ..ui.properties_panels import collider_presets_folder
folder_name = "simple_collider"


def get_default_preferences(context):
    """
    Get the default preferences for the addon.
    """
    prefs = context.preferences.addons[base_package].preferences

    # Extract attribute names from COLLISION_preset.preset_values
    attributes = [attr.split('.')[-1] for attr in COLLISION_preset.preset_values]

    default_prefs = {f"prefs.{attr}": getattr(prefs, attr) for attr in attributes}
    return default_prefs


class UpgradeSimpleColliderPresetsOperator(Operator):
    """
    Operator to upgrade old collider tools preset files to the new format.
    """
    bl_idname = "object.upgrade_simple_collider_presets"
    bl_label = "Upgrade Presets"

    def execute(self, context):
        """
        Executes the operator to upgrade old preset files to the new format.
        """
        preset_folder = collider_presets_folder()

        # Ensure the directory is valid
        if not os.path.isdir(preset_folder):
            self.report({'ERROR'}, "Invalid directory")
            return {'CANCELLED'}

        default_properties = get_default_preferences(context)

        # Iterate over all preset files in the directory
        for filename in os.listdir(preset_folder):
            if filename.endswith(".py"):
                file_path = os.path.join(preset_folder, filename)
                self.upgrade_preset(file_path, default_properties)

        self.report({'INFO'}, "Presets upgraded successfully")
        return {'FINISHED'}

    def upgrade_preset(self, file_path, default_properties):
        """
        Upgrades an old preset file to the new format.
        """
        with open(file_path, 'r') as file:
            lines = file.readlines()

        # Find all existing properties in the old preset and their values
        existing_properties = {}
        for line in lines:
            if line.startswith("prefs."):
                key, value = line.split(' = ')
                existing_properties[key.strip()] = value.strip()

        # Create the new preset template
        new_lines = [
            f"import bpy\n\n",
            f"prefs = bpy.context.preferences.addons['{base_package}'].preferences\n\n"
        ]

        # Transfer existing values to the new template, using default values for missing properties
        for key, default_value in default_properties.items():
            value = existing_properties.get(key, f"'{default_value}'" if isinstance(default_value, str) else default_value)
            new_lines.append(f"{key} = {value}\n")

        # Write the upgraded preset back to the file
        with open(file_path, 'w') as file:
            file.writelines(new_lines)


