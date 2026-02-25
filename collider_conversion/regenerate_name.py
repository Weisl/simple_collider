from bpy.types import Operator

from .. import __package__ as base_package
from ..collider_shapes.add_bounding_primitive import OBJECT_OT_add_bounding_object
from ..properties.constants import VALID_OBJECT_TYPES

default_shape = 'box_shape'
default_group = 'USER_01'


class OBJECT_OT_regenerate_name(Operator):
    """Regenerate selected collider names based on preset"""
    bl_idname = "object.regenerate_name"
    bl_label = "Regenerate Name"
    bl_description = 'Regenerate selected collider names based on preset'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):

        # Convert is only supported in object mode
        if context.mode != 'OBJECT':
            return False

        count = 0
        for obj in context.selected_objects:
            if obj.type in VALID_OBJECT_TYPES:
                count = count + 1
        return count > 0

    def execute(self, context):
        prefs = context.preferences.addons[base_package].preferences
        rename_count = 0
        collider_count = 0
        for obj in context.selected_objects.copy():

            # skip if invalid object
            if obj is None:
                continue

            if obj.type not in VALID_OBJECT_TYPES:
                continue

            if not obj.get('isCollider'):
                continue

            collider_count += 1

            if prefs.replace_name:
                basename = prefs.obj_basename
            elif obj.parent:
                basename = obj.parent.name
            else:
                basename = obj.name

            # get collider shape and group and set to default there is no previous data
            from ..groups.user_groups import get_groups_identifier

            shape_identifier = default_shape if obj.get('collider_shape') is None else obj.get('collider_shape')
            user_group = default_group if obj.get('collider_group') is None else obj.get('collider_group')
            group_identifier = get_groups_identifier(user_group)

            # Find the lowest available name, treating this object's current name as available
            new_name = OBJECT_OT_add_bounding_object.class_collider_name(shape_identifier=shape_identifier,
                                                                         user_group=group_identifier,
                                                                         basename=basename,
                                                                         exclude=obj.name)

            # skip if the object already has the lowest available name
            if new_name == obj.name:
                continue
            obj.name = new_name
            OBJECT_OT_add_bounding_object.set_data_name(obj, new_name, "_data")
            rename_count += 1

        # Show warning if no collider is found
        if collider_count == 0:
            self.report({'WARNING'}, 'No collider to rename')

        # Return CANCELLED to avoid modifying the undo stack when nothing changed
        if rename_count == 0:
            return {'CANCELLED'}

        return {'FINISHED'}
