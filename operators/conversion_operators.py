import bmesh
import bpy
from bpy.types import Operator
from .add_bounding_primitive import OBJECT_OT_add_bounding_object
from ..pyshics_materials.material_functions import set_material, make_physics_material, remove_materials

collider_shapes = ['meshColSuffix', 'boxColSuffix','sphereColSuffix', 'convexColSuffix']


def create_name_number(name, nr):
    nr = str('_{num:{fill}{width}}'.format(num=(nr), fill='0', width=3))
    return name + nr

def unique_name(name, i = 1):
    '''recursive function to find unique name'''
    new_name = create_name_number(name, i)
    while new_name in bpy.data.objects:
        i=i+1
        new_name = create_name_number(name, i)
    return new_name


class OBJECT_OT_convert_to_collider(OBJECT_OT_add_bounding_object, Operator):
    """Convert existing objects to be a collider"""
    bl_idname = "object.convert_to_collider"
    bl_label = "Mesh to Collider"
    bl_description = 'Convert selected meshes to colliders'

    def set_name_suffix(self):
        suffix = self.collider_shapes[self.collider_shapes_idx]

        if suffix == 'boxColSuffix':
            self.type_suffix = self.prefs.boxColSuffix
        elif suffix == 'sphereColSuffix':
            self.type_suffix = self.prefs.sphereColSuffix
        elif suffix == 'convexColSuffix':
            self.type_suffix = self.prefs.convexColSuffix
        else:  # suffix == 'meshColSuffix'
            self.type_suffix = self.prefs.meshColSuffix

    def __init__(self):
        super().__init__()
        self.use_type_change = True
        self.use_decimation = True
        self.is_mesh_to_collider = True

    def invoke(self, context, event):
        super().invoke(context, event)
        self.collider_shapes_idx = 0
        self.collider_shapes = collider_shapes
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        status = super().modal(context, event)
        if status == {'FINISHED'}:
            return {'FINISHED'}
        if status == {'CANCELLED'}:
            return {'CANCELLED'}

        elif event.type == 'C' and event.value == 'RELEASE':
            #toggle through display modes
            self.collider_shapes_idx = (self.collider_shapes_idx + 1) % len(self.collider_shapes)
            self.set_name_suffix()
            self.update_names()

        return {'RUNNING_MODAL'}

    def store_initial_obj_state(self, obj):
        dic = {}
        dic['name'] = obj.name
        dic['material_slots'] = []

        for mat in obj.material_slots:
            dic['material_slots'].append(mat.name)

        dic['color'] = [obj.color[0],obj.color[1],obj.color[2],obj.color[3]]
        dic['show_wire'] = obj.show_wire
        return dic

    def execute(self, context):
        # CLEANUP and INIT
        super().execute(context)

        self.original_obj_data = []
        self.type_suffix = self.prefs.meshColSuffix

        # Create the bounding geometry, depending on edit or object mode.
        for obj in self.selected_objects:

            # skip if invalid object
            if obj is None:
                continue

            # skip non Mesh objects like lamps, curves etc.
            if obj.type != "MESH":
                continue
            new_collider = obj

            self.new_colliders_list.append(new_collider)
            self.original_obj_data.append(self.store_initial_obj_state(obj))

            collections = new_collider.users_collection
            self.primitive_postprocessing(context, new_collider, collections)

            new_collider.name = super().collider_name(basename=obj.name)

        # shape = self.get_shape_name(self.collider_shapes[self.collider_shapes_idx])
        label = "Mesh To Collider"
        super().print_generation_time(label)
        return {'RUNNING_MODAL'}

class OBJECT_OT_convert_to_mesh(Operator):
    """Convert existing objects to be a collider"""
    bl_idname = "object.convert_to_mesh"
    bl_label = "Collider to Mesh"
    bl_description = 'Convert selected colliders to meshes'

    my_string: bpy.props.StringProperty(name="Mesh Name", default='Mesh')

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        col = layout.column()

        row = col.row()
        col.prop(self, "my_string")

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def execute(self, context):
        scene = context.scene

        for obj in bpy.context.selected_objects.copy():
            if obj.get('isCollider'):
                #Reste object properties to regular mesh
                obj['isCollider'] = False
                obj.color = (1, 1, 1, 1)
                obj.name = unique_name(self.my_string)
                obj.display_type = 'TEXTURED'

                # replace collision material
                remove_materials(obj)
                if scene.DefaultMeshMaterial:
                    set_material(obj, scene.DefaultMeshMaterial)
                else:
                    default_material = make_physics_material('Material', (1, 1, 1, 1))
                    bpy.context.scene.DefaultMeshMaterial = default_material
                    set_material(obj, default_material)

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

