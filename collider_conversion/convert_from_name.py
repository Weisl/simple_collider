import bpy
import re

from bpy.types import Operator
from ..groups.user_groups import get_groups_color, set_object_color, get_groups_identifier

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

        col_prefix = prefs.collision_string_suffix
        col_suffix = prefs.collision_string_prefix

        separator = prefs.separator

        user_group_01 = str(prefs.user_group_01)
        user_group_02 = str(prefs.user_group_02)
        user_group_03 = str(prefs.user_group_03)

        print(user_group_01)
        print(user_group_02)
        print(user_group_03)

        box_shape = prefs.box_shape
        sphere_shape = prefs.sphere_shape
        capsule_shape = prefs.capsule_shape
        convex_shape = prefs.convex_shape
        mesh_shape = prefs.mesh_shape

        ignore_case = True

        for obj in bpy.context.selected_objects.copy():

            # skip if invalid object
            if obj is None:
                continue

            name = obj.name

            isCollider = False

            # Dynamically create the regex pattern
            pattern1 = re.compile(fr'(^|{separator}){col_prefix}({separator}|$)', re.IGNORECASE)
            pattern2 = re.compile(fr'(^|{separator}){col_suffix}({separator}|$)', re.IGNORECASE)

            # Check for collider identifier
            if (col_prefix and pattern1.search(name)) or (col_suffix and pattern2.search(name)):
                isCollider = True

            # Check Collider Groups
            if prefs.collider_groups_enabled:
                color = [1, 1, 1, 1]
                grouped = False

                # Dynamically create the regex pattern
                pattern_group1 = re.compile(fr'(^|{separator}){user_group_01}({separator}|$)', re.IGNORECASE)
                pattern_group2 = re.compile(fr'(^|{separator}){user_group_02}({separator}|$)', re.IGNORECASE)
                pattern_group3 = re.compile(fr'(^|{separator}){user_group_03}({separator}|$)', re.IGNORECASE)

                if user_group_01 and pattern_group1.search(name):
                    obj['collider_group'] = 'USER_01'
                    color = get_groups_color('USER_01')
                    isCollider = True
                    grouped = True

                elif user_group_02 and pattern_group2.search(name):
                    obj['collider_group'] = 'USER_02'
                    color = get_groups_color('USER_02')
                    isCollider = True
                    grouped = True

                elif user_group_03 and pattern_group3.search(name):
                    obj['collider_group'] = 'USER_03'
                    color = get_groups_color('USER_03')
                    isCollider = True
                    grouped = True

                if grouped:
                    alpha = prefs.user_groups_alpha
                    set_object_color(obj, (color[0], color[1], color[2], alpha))


            # Collider Shape
            pattern_box_shape = re.compile(fr'(^|{separator}){box_shape}({separator}|$)', re.IGNORECASE)
            pattern_sphere_shape = re.compile(fr'(^|{separator}){sphere_shape}({separator}|$)', re.IGNORECASE)
            pattern_capsule_shape = re.compile(fr'(^|{separator}){capsule_shape}({separator}|$)', re.IGNORECASE)
            pattern_convex_shape = re.compile(fr'(^|{separator}){convex_shape}({separator}|$)', re.IGNORECASE)
            pattern_mesh_shape = re.compile(fr'(^|{separator}){mesh_shape}({separator}|$)', re.IGNORECASE)

            if box_shape and pattern_box_shape.search(name):
                obj['collider_shape'] = 'box_shape'
                isCollider = True

            elif sphere_shape and pattern_sphere_shape.search(name):
                obj['collider_shape'] = 'sphere_shape'
                isCollider = True

            elif capsule_shape and pattern_capsule_shape.search(name):
                obj['collider_shape'] = 'capsule_shape'
                isCollider = True

            elif convex_shape and pattern_convex_shape.search(name):
                obj['collider_shape'] = 'convex_shape'
                isCollider = True

            elif mesh_shape and pattern_mesh_shape.search(name):
                obj['collider_shape'] = 'mesh_shape'
                isCollider = True


            if isCollider:
                obj['isCollider'] = True
                count = count + 1

        if count == 0:
            self.report({'WARNING'}, 'No collider has been detected')
        else:
            self.report({'INFO'}, f"{count} colliders have been converted")

        return {'FINISHED'}
