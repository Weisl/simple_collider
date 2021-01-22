import bpy
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

        pie.operator("mesh.add_bounding_box")
        pie.operator("mesh.add_bounding_cylinder")
        pie.operator("mesh.add_bounding_sphere")