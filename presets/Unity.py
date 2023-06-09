import bpy
prefs = bpy.context.preferences.addons['collider_tools'].preferences

prefs.naming_position = 'SUFFIX'
prefs.replace_name = True
prefs.obj_basename = 'Collider'
prefs.separator = '_'
prefs.collision_string_prefix = ''
prefs.collision_string_suffix = ''
prefs.box_shape = 'Box'
prefs.sphere_shape = 'Sphere'
prefs.capsule_shape = 'Capsule'
prefs.convex_shape = 'Convex'
prefs.mesh_shape = 'Mesh'
prefs.collider_groups_enabled = True
prefs.user_group_01 = 'SimpleComplex'
prefs.user_group_02 = 'Simple'
prefs.user_group_03 = 'Complex'
prefs.user_group_01_name = 'Simple Complex'
prefs.user_group_02_name = 'Simple'
prefs.user_group_03_name = 'Complex'
prefs.use_physics_material = True
prefs.material_naming_position = 'PREFIX'
prefs.physics_material_separator = '_'
prefs.use_random_color = True
prefs.physics_material_su_prefix = 'COL'
prefs.physics_material_name = 'COL_DEFAULT'
prefs.physics_material_filter = 'COL'
