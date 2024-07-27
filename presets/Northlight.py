import bpy

prefs = bpy.context.preferences.addons['collider_tools'].preferences

prefs.naming_position = 'SUFFIX'
prefs.replace_name = False
prefs.obj_basename = 'Collider'
prefs.separator = '_'
prefs.collision_string_prefix = 'COL'
prefs.collision_string_suffix = ''
prefs.box_shape = 'BOX'
prefs.sphere_shape = 'SPHERE'
prefs.capsule_shape = 'CAPSULE'
prefs.convex_shape = 'CONVEX'
prefs.mesh_shape = 'MESH'
prefs.collider_groups_enabled = True
prefs.user_group_01 = 'LOW_HIGH'
prefs.user_group_02 = 'LOW'
prefs.user_group_03 = 'HIGH'
prefs.user_group_01_name = 'Low High'
prefs.user_group_02_name = 'Low'
prefs.user_group_03_name = 'High'
prefs.use_physics_material = True
prefs.material_naming_position = 'PREFIX'
prefs.physics_material_separator = '_'
prefs.use_random_color = True
prefs.physics_material_su_prefix = 'COL'
prefs.physics_material_name = 'COL_DEFAULT'
prefs.physics_material_filter = 'COL'
