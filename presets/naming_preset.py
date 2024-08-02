from bl_operators.presets import AddPresetBase
from bpy.types import Operator

from .. import __package__ as base_package

# Set ADDON_NAME based on __package__, with a fallback for direct script execution
ADDON_NAME = base_package if base_package else "collider_tools"
folder_name = 'collider_tools'


class COLLISION_preset(AddPresetBase, Operator):
    """Presets for collider creation"""
    bl_idname = "collision.collision_name_preset"
    bl_label = "Collision Naming Presets"
    preset_menu = "OBJECT_MT_collision_presets"

    # Common variable used for all preset values
    preset_defines = [

        f'prefs = bpy.context.preferences.addons["{ADDON_NAME}"].preferences',
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
        "prefs.rigid_body_naming_position",
        "prefs.rigid_body_extension",
        "prefs.rigid_body_separator",
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

    # Directory to store the presets
    preset_subdir = folder_name