import bmesh
import bpy
from bpy.types import Operator
from .add_bounding_primitive import OBJECT_OT_add_bounding_object

collider_shapes = ['boxColSuffix','sphereColSuffix', 'convexColSuffix', 'meshColSuffix']


def create_name_number(name, nr):
    nr = str('_{num:{fill}{width}}'.format(num=(nr), fill='0', width=3))
    return name + nr

def unique_name(name, i = 1):
    '''recursive function to find unique name'''
    new_name = create_name_number(name, i)
    while new_name in bpy.data.objects:
        i = i+1
        new_name = create_name_number(name, i)
    return new_name


class OBJECT_OT_convert_to_collider(OBJECT_OT_add_bounding_object, Operator):
    """Convert existing objects to be a collider"""
    bl_idname = "object.convert_to_collider"
    bl_label = "Convert to Collider"

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

    def execute(self, context):
        # CLEANUP and INIT
        super().execute(context)

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

            collections = new_collider.users_collection
            self.primitive_postprocessing(context, new_collider, collections, self.physics_material_name)

            new_collider.name = super().collider_name(basename=obj.name)

        return {'RUNNING_MODAL'}

class OBJECT_OT_convert_to_mesh(Operator):
    """Convert existing objects to be a collider"""
    bl_idname = "object.convert_to_mesh"
    bl_label = "Convert to Mesh"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        for obj in bpy.context.selected_objects:
            if obj.get('isCollider'):
                obj['isCollider'] = False
                obj.color = (1, 1, 1, 1)
                obj.name = unique_name('mesh')
        return {'FINISHED'}

