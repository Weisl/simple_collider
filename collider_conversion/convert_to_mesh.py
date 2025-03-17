import bpy
from bpy.types import Operator

from .. import __package__ as base_package
from ..collider_shapes.add_bounding_primitive import OBJECT_OT_add_bounding_object
from ..pyshics_materials.material_functions import assign_physics_material, create_material, remove_materials

default_shape = 'box_shape'
default_group = 'USER_01'


class OBJECT_OT_convert_to_mesh(Operator):
    """Convert selected colliders to mesh objects"""
    bl_idname = "object.convert_to_mesh"
    bl_label = "Collider to Mesh"
    bl_description = 'Convert selected colliders to meshes'

    mesh_name: bpy.props.StringProperty(name="Mesh Name", default='Mesh')
    keep_original_material: bpy.props.BoolProperty(name="Keep Material", default=False)

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        col = layout.column()

        row = col.row()
        row.prop(self, "mesh_name")

        # row = col.row()
        # row.prop(data, "DefaultMeshMaterial", text='Material')
        row = col.row()
        row.prop(self, "keep_original_material", text='Keep Material')

    @classmethod
    def poll(cls, context):
        count = 0
        if context.mode != 'OBJECT':
            return False

        for obj in context.selected_objects:
            if obj.type in ['MESH', 'CURVE', 'SURFACE', 'FONT', 'META']:
                count = count + 1
        return count > 0

    def execute(self, context):
        colSettings = context.scene.simple_collider
        count = 0

        for obj in bpy.context.selected_objects.copy():
            if obj.get('isCollider'):
                count += 1
                # Rest object properties to regular mesh
                obj['isCollider'] = False
                obj.color = (1, 1, 1, 1)
                obj.name = OBJECT_OT_add_bounding_object.unique_name(self.mesh_name)
                obj.display_type = 'TEXTURED'

                if self.keep_original_material == False:
                    remove_materials(obj)

                    # replace collision material
                    if colSettings.defaultMeshMaterial:
                        assign_physics_material(obj, colSettings.defaultMeshMaterial.name)
                    else:
                        default_material = create_material('Material', (1, 1, 1, 1))
                        colSettings.defaultMeshMaterial = default_material
                        assign_physics_material(obj, default_material.name)

                # remove from collision collection
                prefs = context.preferences.addons[base_package].preferences
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
