import bpy
from bpy.types import Operator

from ..collider_shapes.add_bounding_primitive import OBJECT_OT_add_bounding_object
from ..pyshics_materials.material_functions import set_physics_material, create_material, remove_materials


class OBJECT_OT_regenerate_name(Operator):
    """Regenerate collider names based on prefab"""
    bl_idname = "object.regenerate_name"
    bl_label = "Regenerate Name"
    bl_description = 'Regenerate collider names based on prefab'

    @classmethod
    def poll(cls, context):
        count = 0
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                count = count + 1
        return count > 0

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.parent:
                shape_identifier = obj.get('obj_collider_shape')
                user_group = obj.get('obj_collider_group')

                if shape_identifier and user_group:
                    obj.name = OBJECT_OT_add_bounding_object.class_collider_name(shape_identifier, user_group,
                                                                                 basename=obj.parent.name)


class OBJECT_OT_convert_to_collider(OBJECT_OT_add_bounding_object, Operator):
    """Convert existing objects to be a collider"""
    bl_idname = "object.convert_to_collider"
    bl_label = "Mesh to Collider"
    bl_description = 'Convert selected meshes to colliders'

    def __init__(self):
        super().__init__()
        self.use_shape_change = True
        self.use_decimation = True
        self.is_mesh_to_collider = True

    def invoke(self, context, event):
        super().invoke(context, event)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        status = super().modal(context, event)
        if status == {'FINISHED'}:
            return {'FINISHED'}
        if status == {'CANCELLED'}:
            return {'CANCELLED'}
        if status == {'PASS_THROUGH'}:
            return {'PASS_THROUGH'}


        elif event.type == 'Q' and event.value == 'RELEASE':
            # toggle through display modes
            self.collider_shapes_idx = (self.collider_shapes_idx + 1) % len(self.collider_shapes)
            self.shape_suffix = self.prefs[self.collider_shapes[self.collider_shapes_idx]]
            self.update_names()

        return {'RUNNING_MODAL'}

    def store_initial_obj_state(self, obj):
        dic = {}
        dic['name'] = obj.name
        dic['material_slots'] = []

        for mat in obj.material_slots:
            dic['material_slots'].append(mat.name)

        dic['color'] = [obj.color[0], obj.color[1], obj.color[2], obj.color[3]]
        dic['show_wire'] = obj.show_wire
        return dic

    def execute(self, context):
        # CLEANUP and INIT
        super().execute(context)

        self.original_obj_data = []
        self.shape_suffix = self.prefs.mesh_shape_identifier

        # Create the bounding geometry, depending on edit or object mode.
        for obj in self.selected_objects:

            # skip if invalid object
            if not self.is_valid_object(obj):
                continue

            new_collider = obj

            self.new_colliders_list.append(new_collider)
            self.original_obj_data.append(self.store_initial_obj_state(obj))

            collections = new_collider.users_collection
            self.primitive_postprocessing(context, new_collider, collections)

            new_name = super().collider_name(basename=obj.name)
            new_collider.name = new_name
            new_collider.data.name = new_name + self.data_suffix
            new_collider.data.name = new_name + self.data_suffix

        # shape = self.get_shape_name(self.collider_shapes[self.collider_shapes_idx])
        label = "Mesh To Collider"
        super().print_generation_time(label)
        return {'RUNNING_MODAL'}


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
        count = 0
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                count = count + 1
        return count > 0

    def execute(self, context):
        scene = context.scene

        for obj in bpy.context.selected_objects.copy():
            if obj.get('isCollider'):
                # Reste object properties to regular mesh
                obj['isCollider'] = False
                obj.color = (1, 1, 1, 1)
                obj.name = self.unique_name(self.my_string)
                obj.display_type = 'TEXTURED'

                # replace collision material
                remove_materials(obj)
                if scene.DefaultMeshMaterial:
                    set_physics_material(obj, scene.DefaultMeshMaterial.name)
                else:
                    default_material = create_material('Material', (1, 1, 1, 1))
                    bpy.context.scene.DefaultMeshMaterial = default_material
                    set_physics_material(obj, default_material.name)

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

        return {'FINISHED'}
