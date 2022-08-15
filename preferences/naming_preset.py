from bl_operators.presets import AddPresetBase
from bpy.types import Operator

class COLLISION_preset(AddPresetBase, Operator):
    '''Naming presets for collisions'''
    bl_idname = "collision.collision_name_preset"
    bl_label = "Collision Naming Presets"
    preset_menu = "OBJECT_MT_collision_presets"

    # variable used for all preset values
    preset_defines = [
        "prefs = bpy.context.preferences.addons['collider_tools'].preferences"
    ]

    # properties to store in the preset
    preset_values = [
        "prefs.naming_position",
        "prefs.separator",
        "prefs.basename",
        "prefs.replace_name",
        "prefs.colPreSuffix",
        "prefs.optionalSuffix",
        "prefs.IgnoreShapeForComplex",
        "prefs.colSimpleComplex",
        "prefs.colSimple",
        "prefs.colComplex",
        "prefs.boxColSuffix",
        "prefs.convexColSuffix",
        "prefs.sphereColSuffix",
        "prefs.meshColSuffix",
    ]

    # where to store the preset
    preset_subdir = "collider_tools"
