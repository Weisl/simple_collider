import bpy
import re
from .. import __package__ as base_package
from ..collider_shapes.add_bounding_primitive import OBJECT_OT_add_bounding_object

class COLLISION_OT_assign_shape(bpy.types.Operator):
    """Select/Deselect collision objects"""
    bl_idname = "object.assign_collider_shape"
    bl_label = "Assign Collider Shape"
    bl_description = 'Assign shape to a collider'
    bl_options = {"REGISTER", "UNDO"}

    shape_identifier: bpy.props.StringProperty()

    regex_search_patterns = None  # Class-level cache for regex patterns

    @classmethod
    def poll(cls, context):
        """Ensure at least one valid object is selected."""
        return any(obj.type in ['MESH', 'CURVE', 'SURFACE', 'FONT', 'META'] for obj in context.selected_objects)

    def compile_regex_patterns(self, shapes, separator):
        """Precompile regex patterns for all shapes."""
        if not self.regex_search_patterns:
            self.regex_search_patterns = {
                shape: re.compile(fr'(?:^|{separator})({shape})(?:{separator}|$)', re.IGNORECASE)
                for shape in shapes if shape
            }

    def is_valid_object(self, obj):
        """Check if the object is valid for processing."""
        return obj and obj.type in ['MESH', 'CURVE', 'SURFACE', 'FONT', 'META'] and obj.get('isCollider')

    def replace_shape(self, name, from_shape, to_shape):
        """Replace a specific shape with another in the object name."""
        if not from_shape or not to_shape:
            return name

        pattern = self.regex_search_patterns.get(from_shape)
        if not pattern:
            return name

        # Perform the replacement, preserving separators
        return pattern.sub(lambda m: f"{m.group(0).replace(from_shape, to_shape)}", name)

    def execute(self, context):
        prefs = context.preferences.addons[base_package].preferences


        # Get naming presets
        separator = prefs.separator

        # Retrieve all shape names
        shapes = [
            prefs.box_shape,
            prefs.sphere_shape,
            prefs.capsule_shape,
            prefs.convex_shape,
            prefs.mesh_shape,
        ]

        # Compile regex patterns once
        self.compile_regex_patterns(shapes, separator)

        count = 0
        for obj in list(context.selected_objects):
            # Skip invalid objects
            if not self.is_valid_object(obj):
                continue

            count += 1

            # Start with the current object name
            new_name = obj.name

            # Assign collider shape
            obj['collider_shape'] = self.shape_identifier
            shape_name = OBJECT_OT_add_bounding_object.get_shape_pre_suffix(prefs, self.shape_identifier)

            # Replace shapes in the object name
            for from_shape in shapes:
                new_name = self.replace_shape(new_name, from_shape, shape_name)

            # Update object name and data name
            obj.name = new_name
            OBJECT_OT_add_bounding_object.set_data_name(obj, new_name, "_data")

        if count == 0:
            self.report({'WARNING'}, "No valid colliders found to change the shape type.")
            return {'CANCELLED'}

        return {'FINISHED'}
