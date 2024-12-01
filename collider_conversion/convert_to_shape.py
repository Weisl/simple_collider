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

    @classmethod
    def poll(cls, context):
        # Ensure at least one valid object is selected
        return any(obj.type in ['MESH', 'CURVE', 'SURFACE', 'FONT', 'META'] for obj in context.selected_objects)

    def execute(self, context):
        prefs = context.preferences.addons[base_package].preferences

        # Get naming presets
        separator = prefs.separator
        naming_position = prefs.naming_position

        # Retrieve all shape names
        shapes = [
            prefs.box_shape,
            prefs.sphere_shape,
            prefs.capsule_shape,
            prefs.convex_shape,
            prefs.mesh_shape,
        ]

        # Precompile regex patterns for all shapes
        regex_search_patterns = {
            shape: re.compile(fr'(?:^|{separator})({shape})(?:{separator}|$)', re.IGNORECASE)
            for shape in shapes
        }


        def replace_shape(name, from_shape, to_shape):
            """Replace a specific shape with another in the object name."""
            pattern = regex_search_patterns[from_shape]
            return pattern.sub(
                lambda m: f"{separator}{to_shape}{separator}".strip(separator), name
            )

        count = 0
        for obj in context.selected_objects.copy():

            # Skip invalid objects
            if (
                obj is None
                or obj.type not in ['MESH', 'CURVE', 'SURFACE', 'FONT', 'META']
                or not obj.get('isCollider')
            ):
                continue

            count += 1

            # Start with the current object name
            new_name = obj.name

            obj['collider_shape'] = self.shape_identifier
            shape_name = OBJECT_OT_add_bounding_object.get_shape_pre_suffix(prefs, self.shape_identifier)

            # Remove existing shapes and replace them with the selected one
            for from_shape in shapes:
                if from_shape != self.shape_identifier:  # Only replace different shapes
                    new_name = replace_shape(new_name, from_shape, shape_name)


            # Assign the new name to the object
            obj.name = new_name

            # Update the object's data name
            OBJECT_OT_add_bounding_object.set_data_name(obj, new_name, "_data")

        # Report if no colliders were found
        if count == 0:
            self.report({'WARNING'}, "No collider found to change the shape type.")
            return {'CANCELLED'}

        return {'FINISHED'}

