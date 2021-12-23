from .properties_panels import visibility_operators
from bpy.types import Menu

# spawn an edit mode selection pie (run while object is in edit mode to get a valid output)
class VIEW3D_MT_collision(Menu):
    bl_label = 'Collision Visibility'

    def draw(self, context):
        col = self.layout.column_flow(columns=5, align = True)

        for value in visibility_operators:
            col.label(text=value)

        for key, value in visibility_operators.items():
            # op = col.operator("object.hide_collisions", icon='HIDE_OFF', text=value)
            op = col.operator("object.hide_collisions", icon='HIDE_OFF', text='')
            op.hide = False
            op.mode = key

        for key, value in visibility_operators.items():
            # op = col.operator("object.hide_collisions", icon='HIDE_ON', text=value)
            op = col.operator("object.hide_collisions", icon='HIDE_ON', text='')
            op.hide = True
            op.mode = key

        for key, value in visibility_operators.items():
            # op = col.operator("object.select_collisions", icon='RESTRICT_SELECT_OFF', text='')
            op = col.operator("object.select_collisions", text='Select')
            op.invert = False
            op.mode = key

        for key, value in visibility_operators.items():
            # op = col.operator("object.select_collisions", icon='RESTRICT_SELECT_ON', text='')
            op = col.operator("object.select_collisions", text='Unselect')
            op.invert = True
            op.mode = key

class VIEW3D_MT_PIE_template(Menu):
    # label is displayed at the center of the pie menu.
    bl_label = "Collision Pie"
    bl_idname = "COLLISION_MT_pie_menu"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        # operator_enum will just spread all available options
        # for the type enum of the operator on the pie

        prefs = context.preferences.addons["CollisionHelpers"].preferences


        #West
        pie.operator("mesh.add_bounding_box", icon='MESH_CUBE')
        #East
        pie.operator("mesh.add_bounding_cylinder", icon='MESH_CYLINDER')
        #South
        other = pie.column()
        # gap = other.column()
        # gap.separator()
        # gap.scale_y = 7
        other_menu = other.box().column()
        # other_menu.scale_x= 2
        other_menu.menu_contents("VIEW3D_MT_collision")

        #North
        pie.operator("mesh.add_bounding_convex_hull", icon='MESH_ICOSPHERE')

        #NorthWest
        pie.operator("mesh.add_mesh_collision", icon='MESH_MONKEY')

        #NorthEast
        pie.operator("mesh.add_bounding_sphere", icon='MESH_UVSPHERE')

        #SouthWest
        pass
        # if prefs.executable_path:
        #     pie.operator("collision.vhacd")
        # else:
        #     pie.operator("wm.url_open", text="Convex decomposition: Requires V-HACD").url = "https://github.com/kmammou/v-hacd"
        #
