import bpy
from bpy.types import Operator
import re

class OBJECT_OT_convert_from_name(Operator):
    """Convert selected colliders to mesh objects"""
    bl_idname = "object.convert_from_name"
    bl_label = "Collider from Naming"
    bl_description = 'Assign collider attributes from the object naming.'


    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def execute(self, context):
        colSettings = context.scene.collider_tools
        count = 0

        prefs = context.preferences.addons[__package__.split('.')[0]].preferences

        for obj in bpy.context.selected_objects.copy():
            name = obj.name

            col_suffix = prefs.collision_string_suffix
            col_prefix = prefs.collision_string_prefix

            isCollider = False

            user_group_01 = prefs.user_group_01,
            user_group_02 = prefs.user_group_02,
            user_group_03 = prefs.user_group_03


            regexp = re.compile(str(user_group_03))
            if regexp.search(name):
                obj['collider_group'] = 'USER_03'

                isCollider = True

            regexp = re.compile(str(user_group_02))
            if regexp.search(name):
                obj['collider_group'] = 'USER_02'
                isCollider = True

            regexp = re.compile(str(user_group_01))
            if regexp.search(name):
                obj['collider_group'] = 'USER_01'
                isCollider = True


            shape = prefs.box_shape
            regexp = re.compile(str(shape))
            if regexp.search(name):
                obj['collider_shape'] = 'box_shape'
                isCollider = True

            shape = prefs.sphere_shape
            regexp = re.compile(str(shape))
            if regexp.search(name):
                obj['collider_shape'] = 'sphere_shape'
                isCollider = True

            shape = prefs.capsule_shape
            regexp = re.compile(str(shape))
            if regexp.search(name):
                obj['collider_shape'] = 'capsule_shape'
                isCollider = True

            shape = prefs.convex_shape
            regexp = re.compile(str(shape))
            if regexp.search(name):
                obj['collider_shape'] = 'convex_shape'
                isCollider = True

            shape = prefs.mesh_shape
            regexp = re.compile(str(shape))
            if regexp.search(name):
                obj['collider_shape'] = 'mesh_shape'
                isCollider = True

            if isCollider:
                obj['isCollider'] = True


        if count == 0:
            self.report({'WARNING'}, 'No collider has been detected')
        else:
            self.report({'INFO'}, f"{count} colliders have been converted")

        return {'FINISHED'}