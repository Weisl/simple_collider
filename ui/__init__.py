from . import properties_panels
from . import pie_menu

classes = (
    properties_panels.PREFERENCES_OT_open_addon,
    properties_panels.VIEW3D_PT_collission_panel,
    properties_panels.VIEW3D_PT_collission_visibility_panel,
    properties_panels.VIEW3D_PT_collission_settings_panel,
    properties_panels.VIEW3D_PT_collission_material_panel,
    pie_menu.VIEW3D_MT_collision,
    pie_menu.VIEW3D_MT_PIE_template,
)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
