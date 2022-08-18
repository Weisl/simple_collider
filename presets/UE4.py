import bpy

prefs = bpy.context.preferences.addons['collider_tools'].preferences

prefs.naming_position = 'PREFIX'
prefs.replace_name = False
prefs.basename = 'geo'
prefs.separator = '_'
prefs.collision_string_prefix = ''
prefs.collision_string_suffix = ''
prefs.box_shape_identifier = 'UBX'
prefs.sphere_shape_identifier = 'USP'
prefs.convex_shape_identifier = 'UCX'
prefs.mesh_shape_identifier = ''
prefs.collider_groups_enabled = True
prefs.collider_groups_naming_use = True
prefs.user_group_01 = ''
prefs.user_group_02 = ''
prefs.user_group_03 = 'Complex'
prefs.physics_material_name = 'MI_COL'
prefs.physics_material_filter = 'COL'

