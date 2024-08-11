import bpy
from .presets_data import presets
from .. import __package__ as base_package


class SetColliderToolsPreferencesOperator(bpy.types.Operator):
    """
    Operator to set the preferences for the 'simple_collider' addon based on a selected preset.
    """
    bl_idname = "object.set_collider_tools_prefs"
    bl_label = "Set Simple Collider Preferences"
    preset_name: bpy.props.StringProperty()

    def execute(self, context):
        prefs = bpy.context.preferences.addons[base_package].preferences
        preset = presets[self.preset_name]

        for key, value in preset.items():
            setattr(prefs, key, value)

        return {'FINISHED'}