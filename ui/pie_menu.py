from bpy.types import Menu


# spawn an edit mode selection pie (run while object is in edit mode to get a valid output)


class VIEW3D_MT_PIE_template(Menu):
    # label is displayed at the center of the pie menu.
    bl_label = "Select Mode"
    bl_idname = "COLLISION_pie_menu"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        # operator_enum will just spread all available options
        # for the type enum of the operator on the pie

        pie.operator("mesh.add_bounding_box", icon='MESH_CUBE')
        pie.operator("mesh.add_bounding_cylinder", icon='MESH_CYLINDER')
        pie.operator("mesh.add_bounding_sphere", icon='MESH_UVSPHERE')
        pie.operator("mesh.add_bounding_convex_hull", icon='MESH_ICOSPHERE')
        pie.operator("mesh.add_mesh_collision", icon='MESH_MONKEY')
        pie.operator("collision.vhacd")
