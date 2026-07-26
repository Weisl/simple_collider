from multiprocessing import context
import bpy
import os
from .. import __package__ as base_package

from .properties_panels import draw_auto_convex_settings
from .properties_panels import draw_auto_convex_coacd_settings
from .properties_panels import get_permission_fix_url


class VIEW3D_PT_auto_convex_popup(bpy.types.Panel):
    """Tooltip"""
    bl_idname = "POPUP_PT_auto_convex"
    bl_label = "Auto Convex Info"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"

    def draw(self, context):
        layout = self.layout

        prefs = context.preferences.addons[base_package].preferences
        default_path = getattr(prefs, 'default_executable_path', '')
        custom_path = getattr(prefs, 'executable_path', '')

        vhacd_path = custom_path if custom_path else default_path

        if vhacd_path and os.path.exists(vhacd_path) and os.access(vhacd_path, os.X_OK):
            colSettings = context.scene.simple_collider
            draw_auto_convex_settings(colSettings, layout)
            layout.label(text='May take up to a few minutes', icon='ERROR')
            layout.operator("collision.vhacd", text="Auto Convex", icon='MESH_ICOSPHERE')
        else:
            layout.label(text="Missing Permission", icon='ERROR')
            row = layout.row()
            row.operator(
                "wm.url_open",
                text="Solution",
                icon='URL'
            ).url = get_permission_fix_url()
        return


class VIEW3D_PT_auto_convex_coacd_popup(bpy.types.Panel):
    """Tooltip"""
    bl_idname = "POPUP_PT_auto_convex_coacd"
    bl_label = "Auto Convex (BETA) Info"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"

    def draw(self, context):
        layout = self.layout

        prefs = context.preferences.addons[base_package].preferences
        default_path = getattr(prefs, 'coacd_default_executable_path', '')
        custom_path = getattr(prefs, 'coacd_executable_path', '')

        coacd_path = custom_path if custom_path else default_path

        if coacd_path and os.path.exists(coacd_path) and os.access(coacd_path, os.X_OK):
            colSettings = context.scene.simple_collider
            draw_auto_convex_coacd_settings(colSettings, layout)
            layout.label(text='May take up to a few minutes', icon='ERROR')
            layout.operator("collision.coacd", text="Auto Convex (BETA)", icon='MESH_ICOSPHERE')
        else:
            layout.label(text="Missing Permission", icon='ERROR')
            row = layout.row()
            row.operator(
                "wm.url_open",
                text="Solution",
                icon='URL'
            ).url = get_permission_fix_url()
        return
