import bpy


class CollissionPanel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "COLLISION_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Pipeline"

    def draw(self, context):
        layout = self.layout

        obj = context.object
        scene = context.scene

        row = layout.row()
        row.operator("mesh.add_box_collision")

        row = layout.row()
        row.operator("mesh.add_cylinder_per_object_collision")

        row = layout.row()
        row.prop(scene, "PhysicsIdentifier")

        row = layout.row()
        row.prop(scene, "CollisionMaterials")


class CollisionMenu(bpy.types.Menu):
    bl_idname = "OBJECT_MT_add_collisions"
    bl_label = "Collisions"

    def draw(self, context):
        layout = self.layout
        layout.operator("mesh.add_box_collision")
        layout.operator("mesh.add_cylinder_per_object_collision")
