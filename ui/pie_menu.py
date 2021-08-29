from bpy.types import Menu


# spawn an edit mode selection pie (run while object is in edit mode to get a valid output)

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
        pie.operator("mesh.add_bounding_sphere", icon='MESH_UVSPHERE')
        #North
        pie.operator("mesh.add_bounding_convex_hull", icon='MESH_ICOSPHERE')
        #NorthWest
        pie.operator("mesh.add_mesh_collision", icon='MESH_MONKEY')

        #NorthEast
        if prefs.executable_path:
            pie.operator("collision.vhacd")
        else:
            pie.operator("wm.url_open", text="Convex decomposition: Requires V-HACD").url = "https://github.com/kmammou/v-hacd"

        #SouthWest
        col = pie.column(align=True)
        col.operator("object.hide_collisions", icon='HIDE_ON', text='Collision').hide = True
        col.operator("object.hide_collisions", icon='HIDE_OFF', text='Collision').hide = False