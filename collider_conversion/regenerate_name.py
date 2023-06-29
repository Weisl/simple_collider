from bpy.types import Operator

from ..collider_shapes.add_bounding_primitive import OBJECT_OT_add_bounding_object

default_shape = 'box_shape'
default_group = 'USER_01'


class OBJECT_OT_regenerate_name(Operator):
    """Regenerate selected collider names based on preset"""
    bl_idname = "object.regenerate_name"
    bl_label = "Regenerate Name"
    bl_description = 'Regenerate selected collider names based on preset'

    @classmethod
    def poll(cls, context):

        # Convert is only supported in object mode
        if context.mode != 'OBJECT':
            return False

        count = 0
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                count = count + 1
        return count > 0

    def execute(self, context):
        prefs = context.preferences.addons[__package__.split('.')[0]].preferences

        for obj in context.selected_objects.copy():

            # skip if invalid object
            if obj is None or obj.type != "MESH":
                continue

            if prefs.replace_name:
                basename = prefs.obj_basename
            elif obj.parent:
                basename = obj.parent.name
            else:
                basename = obj.name

            # get collider shape and group and set to default there is no previous data
            shape_identifier = default_shape if obj.get('collider_shape') is None else obj.get('collider_shape')
            user_group = default_group if obj.get('collider_group') is None else obj.get('collider_group')

            new_name = OBJECT_OT_add_bounding_object.class_collider_name(shape_identifier, user_group,
                                                                         basename=basename)
            obj.name = new_name
            OBJECT_OT_add_bounding_object.set_data_name(obj, new_name, "_data")

        return {'FINISHED'}
