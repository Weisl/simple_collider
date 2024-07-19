import bpy
import re

from .. import __package__ as base_package
from bpy.types import Operator
from ..groups.user_groups import get_groups_color, set_object_color

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

        prefs = context.preferences.addons[base_package].preferences

        for obj in bpy.context.selected_objects.copy():

            # skip if invalid object
            if obj is None:
                continue

            name = obj.name

            isCollider = False

            if name.endswith(prefs.collision_string_suffix):
                isCollider = True
            if name.startswith(prefs.collision_string_prefix):
                isCollider = True

            user_group_01 = prefs.user_group_01,
            user_group_02 = prefs.user_group_02,
            user_group_03 = prefs.user_group_03
            color = [0, 0, 0]

            if prefs.collider_groups_enabled:
                regexp = re.compile(str(user_group_03))
                if regexp.search(name):
                    obj['collider_group'] = 'USER_03'
                    color = get_groups_color('USER_03')
                    isCollider = True

                regexp = re.compile(str(user_group_02))
                if regexp.search(name):
                    obj['collider_group'] = 'USER_02'
                    color = get_groups_color('USER_02')
                    isCollider = True

                regexp = re.compile(str(user_group_01))
                if regexp.search(name):
                    obj['collider_group'] = 'USER_01'
                    color = get_groups_color('USER_01')
                    isCollider = True

                alpha = prefs.user_groups_alpha
                set_object_color(obj, (color[0], color[1], color[2], alpha))

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
