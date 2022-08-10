import bpy


class VIEW3D_OT_object_view(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "view.collider_view_object"
    bl_label = "Solid Shading"
    bl_description = 'Viewport Color type: Object'

    def execute(self, context):
        context.space_data.shading.type = 'SOLID'
        context.space_data.shading.color_type = 'OBJECT'
        return {'FINISHED'}


class VIEW3D_OT_material_view(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "view.collider_view_material"
    bl_label = "Physics Material Shading"
    bl_description = 'Viewport Color type: Physics Material'

    def execute(self, context):
        context.space_data.shading.type = 'SOLID'
        context.space_data.shading.color_type = 'MATERIAL'
        return {'FINISHED'}



