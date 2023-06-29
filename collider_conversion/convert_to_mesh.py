import bpy
from bpy.types import Operator

from ..collider_shapes.add_bounding_primitive import OBJECT_OT_add_bounding_object
from ..pyshics_materials.material_functions import assign_physics_material, create_material, remove_materials

default_shape = 'box_shape'
default_group = 'USER_01'

class OBJECT_OT_convert_to_mesh(Operator):
    """Convert selected colliders to mesh objects"""
    bl_idname = "object.convert_to_mesh"
    bl_label = "Collider to Mesh"
    bl_description = 'Convert selected colliders to meshes'

    my_string: bpy.props.StringProperty(name="Mesh Name", default='Mesh')

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        col = layout.column()

        row = col.row()
        row.prop(self, "my_string")

        row = col.row()
        row.prop(scene, "DefaultMeshMaterial", text='Material')

    @classmethod
    def poll(cls, context):

        # Convert is only supported in object mode
        if context.mode != 'OBJECT':
            return False

        # Objects need to be selected
        count = 0
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                count = count + 1
        return count > 0

    def execute(self, context):
        colSettings = context.scene.collider_tools
        count = 0

        for obj in bpy.context.selected_objects.copy():
            if obj.get('isCollider'):
                count += 1
                # Reste object properties to regular mesh
                obj['isCollider'] = False
                obj.color = (1, 1, 1, 1)
                obj.name = OBJECT_OT_add_bounding_object.unique_name(self.my_string)
                obj.display_type = 'TEXTURED'

                # replace collision material
                remove_materials(obj)
                if colSettings.defaultMeshMaterial:
                    assign_physics_material(obj, colSettings.defaultMeshMaterial.name)
                else:
                    default_material = create_material('Material', (1, 1, 1, 1))
                    colSettings.defaultMeshMaterial = default_material
                    assign_physics_material(obj, default_material.name)

                # remove from collision collection
                prefs = context.preferences.addons[__package__.split('.')[0]].preferences
                collection_name = prefs.col_collection_name

                # remove from collision collection
                for collection in bpy.data.collections:
                    if collection.name == collection_name:
                        if obj.name in collection.objects:
                            collection.objects.unlink(obj)

                            # add to default scene collection if the object is not part of any collection anymore
                            if len(obj.users_collection) == 0:
                                bpy.context.scene.collection.objects.link(obj)

        if count == 0:
            self.report({'WARNING'}, 'No collider selected for conversion')
        else:
            self.report({'INFO'}, f"{count} colliders have been converted")

        return {'FINISHED'}