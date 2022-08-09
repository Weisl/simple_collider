from .properties_panels import visibility_operators, draw_visibility_selection_menu
from bpy.types import Menu

# spawn an edit mode selection pie (run while object is in edit mode to get a valid output)
class VIEW3D_MT_collision(Menu):
    bl_label = 'Collision Visibility'

    def draw(self, context):
        draw_visibility_selection_menu(self.layout)

        self.layout.separator()

        row = self.layout.row(align=True)
        row.operator('object.convert_to_collider', icon='PHYSICS')
        row.operator('object.convert_to_mesh', icon='MESH_MONKEY')

        self.layout.separator()
        scene = context.scene

        prefs = context.preferences.addons[__package__.split('.')[0]].preferences

        row = self.layout.row(align=True)

        if prefs.executable_path:
            row = self.layout.row(align=True)
            row.prop(scene, 'convex_decomp_depth')
            row.prop(scene, 'maxNumVerticesPerCH')

            row = self.layout.row()
            row.operator("collision.vhacd", text="Auto Convex", icon='MESH_ICOSPHERE')
        else:
            from .. import bl_info
            op = row.operator("preferences.addon_search", text="Install V-HACD", icon='ERROR')
            op.addon_name = bl_info["name"]
            op.prefs_tabs = 'VHACD'


class VIEW3D_MT_PIE_template(Menu):
    # label is displayed at the center of the pie menu.
    bl_label = "Collision Pie"
    bl_idname = "COLLISION_MT_pie_menu"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        # operator_enum will just spread all available options
        # for the type enum of the operator on the pie

        #West
        pie.operator("mesh.add_bounding_box", icon='MESH_CUBE')
        pie.operator("mesh.add_minimum_bounding_box", icon='MESH_CUBE')
        #East
        pie.operator("mesh.add_bounding_cylinder", icon='MESH_CYLINDER')
        #South
        other = pie.column()
        other_menu = other.box().column()
        # other_menu.scale_x= 2
        other_menu.menu_contents("VIEW3D_MT_collision")

        #North
        pie.operator("mesh.add_bounding_convex_hull", icon='MESH_ICOSPHERE')

        #NorthWest
        pie.operator("mesh.add_mesh_collision", icon='MESH_MONKEY')

        #NorthEast
        pie.operator("mesh.add_bounding_sphere", icon='MESH_UVSPHERE')
