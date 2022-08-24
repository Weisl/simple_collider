import bpy

prefs = bpy.context.preferences.addons['collider_tools'].preferences

prefs.naming_position = 'SUFFIX'
prefs.replace_name = True
prefs.obj_basename = 'collider'
prefs.separator = '_'
prefs.collision_string_prefix = ''
prefs.collision_string_suffix = ''
prefs.box_shape_identifier = 'Box'
prefs.sphere_shape_identifier = 'Sphere'
prefs.convex_shape_identifier = 'Convex'
prefs.mesh_shape_identifier = 'Mesh'
prefs.collider_groups_enabled = True
prefs.user_group_01 = 'SimpleComplex'
prefs.user_group_02 = 'Simple'
prefs.user_group_03 = 'Complex'
prefs.user_group_01_name = 'Simple Complex'
prefs.user_group_02_name = 'Simple'
prefs.user_group_03_name = 'Complex'
prefs.physics_material_name = 'COL_DEFAULT'
prefs.physics_material_filter = 'COL'