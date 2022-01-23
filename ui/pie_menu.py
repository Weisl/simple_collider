from .properties_panels import visibility_operators
from bpy.types import Menu

# spawn an edit mode selection pie (run while object is in edit mode to get a valid output)
class VIEW3D_MT_collision(Menu):
    bl_label = 'Collision Visibility'

    def draw(self, context):

        split_left = self.layout.split(factor=0.35)
        col_01 = split_left.column()
        col_02 = split_left.column()

        for key, value in visibility_operators.items():
            row1 = col_02.row(align=True)

            col_01.label(text=value)

            # op = col.operator("object.hide_collisions", icon='HIDE_OFF', text=value)
            op = row1.operator("object.hide_collisions", icon='HIDE_OFF', text='')
            op.hide = False
            op.mode = key

            # op = col.operator("object.hide_collisions", icon='HIDE_ON', text=value)
            op = row1.operator("object.hide_collisions", icon='HIDE_ON', text='')
            op.hide = True
            op.mode = key

            # op = col.operator("object.select_collisions", icon='RESTRICT_SELECT_OFF', text='')
            op = row1.operator("object.select_collisions", text='Select')
            op.select = True
            op.mode = key

            # op = col.operator("object.select_collisions", icon='RESTRICT_SELECT_ON', text='')
            op = row1.operator("object.select_collisions", text='Unselect')
            op.select = False
            op.mode = key

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
            row.operator("preferences.addon_search", text="Install V-HACD", icon='ERROR').addon_name = bl_info["name"]

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
