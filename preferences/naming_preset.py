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
        "prefs.replace_name",
        "prefs.basename",
        "prefs.separator",
        "prefs.collision_string_prefix",
        "prefs.collision_string_suffix",
        "prefs.box_shape_identifier",
        "prefs.sphere_shape_identifier",
        "prefs.convex_shape_identifier",
        "prefs.mesh_shape_identifier",
        "prefs.collider_groups_enabled",
        "prefs.collider_groups_naming_use",
        "prefs.user_group_01",
        "prefs.user_group_02",
        "prefs.user_group_03",
        "prefs.physics_material_name",
        "prefs.physics_material_filter",
    ]

    # where to store the preset
    preset_subdir = "collider_tools"
