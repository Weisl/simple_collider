from bl_operators.presets import AddPresetBase
from bpy.types import Operator, Menu

class OBJECT_MT_collision_presets(Menu):
    bl_label = "Naming Preset"
    preset_subdir = "scene/collision_preset"
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset

class COLLISION_preset(AddPresetBase, Operator):
    '''Naming presets for collisions'''
    bl_idname = "collision.collision_name_preset"
    bl_label = "Collision Naming Presets"
    preset_menu = "OBJECT_MT_collision_presets"

    # variable used for all preset values
    preset_defines = [
        "prefs = bpy.context.preferences.addons['CollisionHelpers'].preferences"
    ]

    # properties to store in the preset
    preset_values = [
        "prefs.meshColSuffix",
        "prefs.convexColSuffix",
        "prefs.boxColSuffix",
        "prefs.colPreSuffix",
        "prefs.colSuffix",
        "prefs.sphereColSuffix",
    ]

    # where to store the preset
    preset_subdir = "scene/collision_preset"
