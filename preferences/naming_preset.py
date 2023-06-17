from bl_operators.presets import AddPresetBase
from bpy.types import Operator


class COLLISION_preset(AddPresetBase, Operator):
    '''Presets for collider creation'''
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
        "prefs.obj_basename",
        "prefs.separator",
        "prefs.collision_string_prefix",
        "prefs.collision_string_suffix",
        "prefs.box_shape",
        "prefs.sphere_shape",
        "prefs.capsule_shape",
        "prefs.convex_shape",
        "prefs.mesh_shape",
        "prefs.collider_groups_enabled",
        "prefs.user_group_01",
        "prefs.user_group_02",
        "prefs.user_group_03",
        "prefs.user_group_01_name",
        "prefs.user_group_02_name",
        "prefs.user_group_03_name",
        "prefs.use_physics_material",
        "prefs.material_naming_position",
        "prefs.physics_material_separator",
        "prefs.use_random_color",
        "prefs.physics_material_su_prefix",
        "prefs.physics_material_name",
        "prefs.physics_material_filter",
    ]

    # where to store the preset
    preset_subdir = "collider_tools"
