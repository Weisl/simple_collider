import bpy


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

        row = layout.row(align=True)
        op = row.operator("object.hide_collisions", icon='HIDE_ON', text='All')
        op.hide = True
        op.mode = 'ALL'
        op = row.operator("object.hide_collisions", icon='HIDE_OFF', text='All')
        op.hide = False
        op.mode = 'ALL'
        row = layout.row(align=True)
        op = row.operator("object.hide_collisions", icon='HIDE_ON', text='Simple')
        op.hide = True
        op.mode = 'SIMPLE'
        op = row.operator("object.hide_collisions", icon='HIDE_OFF', text='Simple')
        op.hide = False
        op.mode = 'SIMPLE'
        row = layout.row(align=True)
        op = row.operator("object.hide_collisions", icon='HIDE_ON', text='Complex')
        op.hide = True
        op.mode = 'COMPLEX'
        op = row.operator("object.hide_collisions", icon='HIDE_OFF', text='Complex')
        op.hide = False
        op.mode = 'COMPLEX'

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
