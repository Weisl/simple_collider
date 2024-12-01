import bpy
import re
from .. import __package__ as base_package
from ..collider_shapes.add_bounding_primitive import OBJECT_OT_add_bounding_object

class COLLISION_OT_assign_shape(bpy.types.Operator):
    """Select/Deselect collision objects"""
    bl_idname = "object.assign_collision_shape"
    bl_label = "Assign Collision Shape"
    bl_description = 'Assign shape to a collider'
    bl_options = {"REGISTER", "UNDO"}

    shape_identifier: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        count = 0
        for obj in context.selected_objects:
            if obj.type in ['MESH', 'CURVE', 'SURFACE', 'FONT', 'META']:
                count = count + 1
        return count > 0

    def execute(self, context):
        prefs = context.preferences.addons[base_package].preferences

        # get naming presets:
        separator = prefs.separator
        naming_position = prefs.naming_position

        box_shape = prefs.box_shape
        sphere_shape = prefs.sphere_shape
        capsule_shape = prefs.capsule_shape
        convex_shape = prefs.convex_shape
        mesh_shape = prefs.mesh_shape

        pattern_box_shape = re.compile(fr'(^|{separator}){box_shape}({separator}|$)', re.IGNORECASE)
        pattern_sphere_shape = re.compile(fr'(^|{separator}){sphere_shape}({separator}|$)', re.IGNORECASE)
        pattern_capsule_shape = re.compile(fr'(^|{separator}){capsule_shape}({separator}|$)', re.IGNORECASE)
        pattern_convex_shape = re.compile(fr'(^|{separator}){convex_shape}({separator}|$)', re.IGNORECASE)
        pattern_mesh_shape = re.compile(fr'(^|{separator}){mesh_shape}({separator}|$)', re.IGNORECASE)

        regex_list = [pattern_box_shape, pattern_sphere_shape, pattern_capsule_shape, pattern_convex_shape,
                      pattern_mesh_shape]

        count = 0
        for obj in context.selected_objects.copy():
            # skip if invalid object
            if obj is None or obj.type not in ['MESH', 'CURVE', 'SURFACE', 'FONT', 'META'] or not obj.get('isCollider'):
                continue
            count += 1

            new_name = obj.name
            for regex in regex_list:
                new_name = re.sub(regex, '', new_name)  # Assign the result back to new_name

            obj['collider_shape'] = self.shape_identifier
            shape_name = OBJECT_OT_add_bounding_object.get_shape_pre_suffix(prefs, self.shape_identifier)

            # Add the shape_name as prefix or suffix depending on naming_position
            if naming_position == 'PREFIX':
                new_name = f'{shape_name}{separator}{new_name}'
            else:  # 'SUFFIX'
                new_name = f'{new_name}{separator}{shape_name}'

            obj.name = new_name
            OBJECT_OT_add_bounding_object.set_data_name(obj, new_name, "_data")

        if count == 0:
            self.report({'WARNING'}, "No collider found to change the shape type.")
            return {'CANCELLED'}

        return {'FINISHED'}
