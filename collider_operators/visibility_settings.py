import bpy


class VIEW3D_OT_object_view(bpy.types.Operator):
    """Viewport Color type: Object"""
    bl_idname = "view.collider_view_object"
    bl_label = "Collider Groups Display"
    bl_description = 'Change viewport color type to: Collider Groups'

    def execute(self, context):
        context.scene.display_type = 'SOLID'
        context.space_data.shading.type = 'SOLID'
        context.space_data.shading.color_type = 'OBJECT'
        return {'FINISHED'}


class VIEW3D_OT_material_view(bpy.types.Operator):
    """Viewport Color type: Physics Material"""
    bl_idname = "view.collider_view_material"
    bl_label = "Physics Material Display"
    bl_description = 'Change viewport color type to: Physics Material'

    def execute(self, context):
        context.scene.display_type = 'SOLID'
        context.space_data.shading.type = 'SOLID'
        context.space_data.shading.color_type = 'MATERIAL'
        return {'FINISHED'}
