import bpy
prefs = bpy.context.preferences.addons['collider_tools'].preferences

prefs.naming_position = 'SUFFIX'
prefs.replace_name = False
prefs.obj_basename = 'geo'
prefs.separator = '-'
prefs.collision_string_prefix = ''
prefs.collision_string_suffix = ''
prefs.box_shape = 'convcolonly'
prefs.sphere_shape = 'convcolonly'
prefs.capsule_shape = 'convcolonly'
prefs.convex_shape = 'convcolonly'
prefs.mesh_shape = 'colonly'
prefs.collider_groups_enabled = False
prefs.user_group_01 = ''
prefs.user_group_02 = ''
prefs.user_group_03 = 'Complex'
prefs.user_group_01_name = 'Simple'
prefs.user_group_02_name = 'Simple 2'
prefs.user_group_03_name = 'Complex'
prefs.use_physics_material = False
prefs.material_naming_position = 'PREFIX'
prefs.physics_material_separator = '_'
prefs.use_random_color = True
prefs.physics_material_su_prefix = ''
prefs.physics_material_name = 'MI_COL'
prefs.physics_material_filter = 'COL'
