import bpy
from .. import __package__ as base_package
from ..collider_shapes.add_bounding_primitive import OBJECT_OT_add_bounding_object
from ..groups.user_groups import get_groups_identifier

default_group = 'USER_01'

class COLLISION_OT_assign_shape(bpy.types.Operator):
    """Reassign the collider shape type on selected colliders, updating their names to match"""
    bl_idname = "object.assign_collider_shape"
    bl_label = "Assign Collider Shape"
    bl_description = 'Assign shape to a collider'
    bl_options = {"REGISTER", "UNDO"}

    shape_identifier: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        """Ensure at least one valid object is selected."""
        return any(obj.type in ['MESH', 'CURVE', 'SURFACE', 'FONT', 'META'] for obj in context.selected_objects)

    def execute(self, context):
        prefs = context.preferences.addons[base_package].preferences

        new_shape_name = OBJECT_OT_add_bounding_object.get_shape_pre_suffix(prefs, self.shape_identifier)
        if not new_shape_name:
            self.report({'WARNING'}, "Collider shape name not defined!")

        count = 0
        for obj in list(context.selected_objects):

            if not obj or obj.type not in ['MESH', 'CURVE', 'SURFACE', 'FONT', 'META'] or not obj.get('isCollider'):
                continue

            # Assign collider shape
            obj['collider_shape'] = self.shape_identifier

            if prefs.replace_name:
                basename = prefs.obj_basename
            elif obj.parent:
                basename = obj.parent.name
            else:
                basename = obj.name

            user_group = default_group if obj.get('collider_group') is None else obj.get('collider_group')

            new_name = OBJECT_OT_add_bounding_object.class_collider_name(
                shape_identifier=self.shape_identifier,
                user_group=get_groups_identifier(user_group),
                basename=basename, exclude=obj.name)

            if new_name != obj.name:
                obj.name = new_name
                OBJECT_OT_add_bounding_object.set_data_name(obj, new_name, "_data")

            count += 1

        if count == 0:
            self.report({'WARNING'}, "No valid colliders found to change the shape type.")
            return {'CANCELLED'}

        return {'FINISHED'}
