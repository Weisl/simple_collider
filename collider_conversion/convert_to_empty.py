import bpy
from bpy.types import Operator

from .. import __package__ as base_package
from ..collider_shapes.add_bounding_primitive import OBJECT_OT_add_bounding_object
from ..groups.user_groups import get_groups_identifier

SUPPORTED_SHAPES = {'box_shape', 'sphere_shape'}
DEFAULT_SHAPE = 'box_shape'
DEFAULT_GROUP = 'USER_01'

EMPTY_DISPLAY_TYPE = {
    'box_shape': 'CUBE',
    'sphere_shape': 'SPHERE',
}


class OBJECT_OT_convert_to_empty(Operator):
    """Convert selected box and sphere colliders to empties whose scale encodes the collision shape dimensions"""
    bl_idname = "object.convert_to_empty"
    bl_label = "Collider to Empty"
    bl_description = 'Convert selected box/sphere colliders to empties (scale = half-extents). Compatible with Godot and GTA modding tools.'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode != 'OBJECT':
            return False
        for obj in context.selected_objects:
            if obj.get('isCollider') and obj.get('collider_shape') in SUPPORTED_SHAPES:
                return True
        return False

    def execute(self, context):
        converted = 0
        skipped = 0

        for obj in list(context.selected_objects):
            if not obj.get('isCollider'):
                skipped += 1
                continue

            shape = obj.get('collider_shape')
            if shape not in SUPPORTED_SHAPES:
                skipped += 1
                continue

            # Capture transform and relationships before removing the mesh object
            name = obj.name
            world_matrix = obj.matrix_world.copy()
            parent = obj.parent
            parent_matrix = obj.matrix_parent_inverse.copy()
            collections = list(obj.users_collection)
            dimensions = obj.dimensions.copy()

            # Create the empty
            empty = bpy.data.objects.new(name, None)
            empty.empty_display_type = EMPTY_DISPLAY_TYPE[shape]

            # Place empty in the same collections as the original collider
            for col in collections:
                col.objects.link(empty)

            # Match world transform
            empty.matrix_world = world_matrix

            # Set scale to half-extents so the empty display matches the original shape.
            # For a box of 5x3x2 the empty cube will have scale (2.5, 1.5, 1.0).
            # For a sphere with diameter d the empty sphere will have scale (r, r, r).
            if shape == 'box_shape':
                empty.scale = (
                    max(dimensions.x / 2, 1e-6),
                    max(dimensions.y / 2, 1e-6),
                    max(dimensions.z / 2, 1e-6),
                )
            else:  # sphere_shape — use the largest dimension as diameter
                radius = max(dimensions.x, dimensions.y, dimensions.z) / 2
                radius = max(radius, 1e-6)
                empty.scale = (radius, radius, radius)

            # Restore parent relationship
            if parent:
                empty.parent = parent
                empty.matrix_parent_inverse = parent_matrix

            # Copy collider custom properties so game-engine exporters can still read them
            empty['isCollider'] = True
            empty['collider_shape'] = shape
            collider_group = obj.get('collider_group', DEFAULT_GROUP)
            empty['collider_group'] = collider_group

            # Remove the original mesh collider before renaming to free the original name
            bpy.data.objects.remove(obj, do_unlink=True)

            # Regenerate the name using the addon's naming convention (prefix/suffix from preferences)
            prefs = context.preferences.addons[base_package].preferences
            if prefs.replace_name:
                basename = prefs.obj_basename
            elif parent:
                basename = parent.name
            else:
                basename = name

            new_name = OBJECT_OT_add_bounding_object.class_collider_name(
                shape_identifier=shape,
                user_group=get_groups_identifier(collider_group),
                basename=basename,
            )
            empty.name = new_name

            converted += 1

        if converted == 0:
            self.report({'WARNING'}, 'No supported colliders (box/sphere) selected for conversion')
        else:
            self.report({'INFO'}, f"{converted} collider(s) converted to empties" +
                        (f", {skipped} skipped" if skipped else ""))

        return {'FINISHED'}