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


class CollisionMenu(bpy.types.Menu):
    bl_idname = "COLLISION_MT_Create"
    bl_label = "Collisions"

    def draw(self, context):
        layout = self.layout
        layout.operator("mesh.add_bounding_box")
        layout.operator("mesh.add_bounding_cylinder")