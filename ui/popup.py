import bpy
from .properties_panels import draw_auto_convex_settings

class VIEW3D_PT_auto_convex_popup(bpy.types.Panel):
    """Tooltip"""
    bl_idname = "POPUP_PT_auto_convex"
    bl_label = "Renaming Info"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_ui_units_x = 30

    def draw(self, context):

        layout = self.layout

        colSettings = context.scene.collider_tools
        draw_auto_convex_settings(colSettings, layout)

        layout.operator("collision.vhacd", text="Auto Convex", icon='MESH_ICOSPHERE')

        return