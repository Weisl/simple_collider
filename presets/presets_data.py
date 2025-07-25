# Define the presets as dictionaries
presets = {
    "UE-default": {
        "naming_position": 'PREFIX',
        "replace_name": False,
        "obj_basename": 'geo',
        "separator": '_',
        "collision_string_prefix": '',
        "collision_string_suffix": '',
        "collision_digits": 2,
        "box_shape": 'UBX',
        "sphere_shape": 'USP',
        "capsule_shape": 'UCP',
        "convex_shape": 'UCX',
        "mesh_shape": '',
        "rigid_body_naming_position": 'PREFIX',
        "rigid_body_extension": '',
        "rigid_body_separator": '',
        "collider_groups_enabled": True,
        "user_group_01": '',
        "user_group_02": '',
        "user_group_03": 'Complex',
        "user_group_01_name": 'Simple',
        "user_group_02_name": 'Simple 2',
        "user_group_03_name": 'Complex',
        "use_physics_material": False,
        "material_naming_position": 'PREFIX',
        "physics_material_separator": '_',
        "use_random_color": True,
        "physics_material_su_prefix": 'COL',
        "physics_material_name": 'MI_COL',
        "physics_material_filter": 'COL'
    },
    "Unity-default": {
        "naming_position": 'SUFFIX',
        "replace_name": True,
        "obj_basename": 'Collider',
        "separator": '_',
        "collision_string_prefix": '',
        "collision_string_suffix": '',
        "collision_digits": 3,
        "box_shape": 'Box',
        "sphere_shape": 'Sphere',
        "capsule_shape": 'Capsule',
        "convex_shape": 'Convex',
        "mesh_shape": 'Mesh',
        "rigid_body_naming_position": 'SUFFIX',
        "rigid_body_extension": '',
        "rigid_body_separator": 'Rigidbody',
        "collider_groups_enabled": True,
        "user_group_01": 'SimpleComplex',
        "user_group_02": 'Simple',
        "user_group_03": 'Complex',
        "user_group_01_name": 'Simple Complex',
        "user_group_02_name": 'Simple',
        "user_group_03_name": 'Complex',
        "use_physics_material": True,
        "material_naming_position": 'PREFIX',
        "physics_material_separator": '_',
        "use_random_color": True,
        "physics_material_su_prefix": 'COL',
        "physics_material_name": 'COL_DEFAULT',
        "physics_material_filter": 'COL'
    },
    "Northlight-default": {
        "naming_position": 'SUFFIX',
        "replace_name": False,
        "obj_basename": 'geo',
        "separator": '_',
        "collision_string_prefix": 'COL',
        "collision_string_suffix": '',
        "collision_digits": 3,
        "box_shape": 'BOX',
        "sphere_shape": 'SPHERE',
        "capsule_shape": 'CAPSULE',
        "convex_shape": 'CONVEX',
        "mesh_shape": 'MESH',
        "rigid_body_naming_position": 'SUFFIX',
        "rigid_body_extension": 'RB',
        "rigid_body_separator": '_',
        "collider_groups_enabled": True,
        "user_group_01": 'LOW_HIGH',
        "user_group_02": 'LOW',
        "user_group_03": 'HIGH',
        "user_group_01_name": 'Low High',
        "user_group_02_name": 'Low',
        "user_group_03_name": 'High',
        "use_physics_material": True,
        "material_naming_position": 'PREFIX',
        "physics_material_separator": '_',
        "use_random_color": True,
        "physics_material_su_prefix": 'COL',
        "physics_material_name": 'COL_DEFAULT',
        "physics_material_filter": 'COL'
    },
    "Godot-default": {
        "naming_position": 'SUFFIX',
        "replace_name": False,
        "obj_basename": 'geo',
        "separator": '-',
        "collision_string_prefix": '',
        "collision_string_suffix": '',
        "collision_digits": 3,
        "box_shape": 'convcolonly',
        "sphere_shape": 'convcolonly',
        "capsule_shape": 'convcolonly',
        "convex_shape": 'convcolonly',
        "mesh_shape": 'colonly',
        "rigid_body_naming_position": 'SUFFIX',
        "rigid_body_extension": 'rigid',
        "rigid_body_separator": '-',
        "collider_groups_enabled": False,
        "user_group_01": '',
        "user_group_02": '',
        "user_group_03": 'Complex',
        "user_group_01_name": 'Simple',
        "user_group_02_name": 'Simple 2',
        "user_group_03_name": 'Complex',
        "use_physics_material": False,
        "material_naming_position": 'PREFIX',
        "physics_material_separator": '_',
        "use_random_color": True,
        "physics_material_su_prefix": '',
        "physics_material_name": 'MI_COL',
        "physics_material_filter": 'COL'
    },

}
