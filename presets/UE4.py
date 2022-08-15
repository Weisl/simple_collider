import bpy
prefs = bpy.context.preferences.addons['collider_tools'].preferences

prefs.naming_position = 'PREFIX'
prefs.separator = '_'
prefs.basename = 'geo'
prefs.replace_name = False
prefs.colPreSuffix = ''
prefs.optionalSuffix = ''
prefs.IgnoreShapeForComplex = True
prefs.colSimpleComplex = ''
prefs.colSimple = ''
prefs.colComplex = 'Complex'
prefs.boxColSuffix = 'UBX'
prefs.convexColSuffix = 'UCX'
prefs.sphereColSuffix = 'USP'
prefs.meshColSuffix = ''
