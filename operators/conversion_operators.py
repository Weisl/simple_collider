import bmesh
import bpy
from bpy.types import Operator
from .add_bounding_primitive import OBJECT_OT_add_bounding_object

class OBJECT_OT_convert_to_collider(OBJECT_OT_add_bounding_object, Operator):
    """Convert existing objects to be a collider"""
    bl_idname = "object.convert_to_collider"
    bl_label = "to Collider"

    def invoke(self, context, event):
        super().invoke(context, event)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        status = super().modal(context, event)
        if status == {'FINISHED'}:
            return {'FINISHED'}
        if status == {'CANCELLED'}:
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def execute(self, context):
        # CLEANUP and INIT
        super().execute(context)
        return {'RUNNING_MODAL'}

class OBJECT_OT_convert_to_mesh(Operator):
    """Convert existing objects to be a collider"""
    bl_idname = "object.convert_to_mesh"
    bl_label = "to Mesh"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        for obj in bpy.context.selected_objects:
            if obj.get('isCollider'):
                obj['isCollider'] = False
                obj.color = (1, 1, 1, 1)

        return {'FINISHED'}

