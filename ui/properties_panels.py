import bpy

visibility_operators = {'ALL': 'All',
'SIMPLE': 'Simple',
'COMPLEX': 'Complex',
'SIMPLE_COMPLEX':'Simple and Complex',
}

class CollissionPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Collision Panel"
    bl_idname = "COLLISION_PT_Create"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Pipeline"

    def draw(self, context):
        layout = self.layout

        obj = context.object
        scene = context.scene

        row = layout.row()
        row.operator("mesh.add_bounding_box")

        row = layout.row()
        row.operator("mesh.add_bounding_cylinder")

        row = layout.row()
        row.prop(scene, "PhysicsIdentifier")

        row = layout.row()
        row.prop(scene, "CollisionMaterials")

        global visibility_operators
        col = self.layout.column_flow(columns=5, align = True)

        for value in visibility_operators:
            col.label(text=value)

        for key, value in visibility_operators.items():
            op = col.operator("object.hide_collisions", icon='HIDE_OFF', text='')
            op.hide = False
            op.mode = key

        for key, value in visibility_operators.items():
            op = col.operator("object.hide_collisions", icon='HIDE_ON', text='')
            op.hide = True
            op.mode = key

        for key, value in visibility_operators.items():
            op = col.operator("object.select_collisions", icon='RESTRICT_SELECT_OFF', text='')
            op.invert = False
            op.mode = key

        for key, value in visibility_operators.items():
            op = col.operator("object.select_collisions", icon='RESTRICT_SELECT_ON', text='')
            op.invert = True
            op.mode = key

        row = layout.row(align=True)
        row.operator('object.convert_to_collider')
        row = layout.row(align=True)
        row.operator('object.convert_to_mesh')

        row = layout.row(align=True)
        row.prop(scene,'my_color')
        row = layout.row(align=True)
        row.prop(scene,'my_color_simple')
        row = layout.row(align=True)
        row.prop(scene,'my_color_complex')


        view = context.space_data
        shading = view.shading

        # row = layout.row(align=True)
        # row.prop(shading, "type", text="", expand=True)
        # row = layout.row(align=True)
        # row.prop(shading, "color_type", text="", expand=True)
