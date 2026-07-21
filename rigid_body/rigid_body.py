import bpy

from .. import __package__ as base_package


class OBJECT_OT_make_rigid_body(bpy.types.Operator):
    """Convert object to be a rigid body"""
    bl_idname = "object.set_rigid_body"
    bl_label = "Set Rigid Body"
    bl_description = 'Convert object to be a rigid body'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def execute(self, context):
        prefs = context.preferences.addons[base_package].preferences

        if not prefs.rigid_body_extension:
            self.report({'WARNING'}, "Rigid Body extension not defined!")
            return {'CANCELLED'}

        renamed_count = 0
        for obj in bpy.context.selected_objects.copy():
            new_name = obj.name

            if prefs.rigid_body_naming_position == 'SUFFIX':
                if not obj.name.endswith(prefs.rigid_body_extension):
                    new_name = obj.name + prefs.rigid_body_separator + prefs.rigid_body_extension
            else:
                if not obj.name.startswith(prefs.rigid_body_extension):
                    new_name = prefs.rigid_body_extension + prefs.rigid_body_separator + obj.name

            if new_name != obj.name:
                obj.name = new_name
                renamed_count += 1

        if renamed_count == 0:
            self.report({'WARNING'}, "No object names needed to be changed")
            return {'CANCELLED'}

        return {'FINISHED'}
