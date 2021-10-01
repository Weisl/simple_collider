import bmesh
import bpy
from bpy.types import Operator

from .add_bounding_primitive import OBJECT_OT_add_bounding_object

def apply_all_modifiers(obj):
    for mod in obj.modifiers:
        bpy.ops.object.modifier_apply(modifier=mod.name)


def remove_all_modifiers(obj):
    if obj:
        for mod in obj.modifiers:
            obj.modifiers.remove(mod)


class OBJECT_OT_add_convex_hull(OBJECT_OT_add_bounding_object, Operator):
    """Create a new bounding box object"""
    bl_idname = "mesh.add_bounding_convex_hull"
    bl_label = "Add Convex Hull"

    use_modifier_stack: bpy.props.BoolProperty(
        name='Use Modifier Stack',
        default=False
    )

    def __init__(self):
        super().__init__()
        self.use_decimation = True
        self.use_modifier_stack = True

    def invoke(self, context, event):
        super().invoke(context, event)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        status = super().modal(context, event)
        if status == {'FINISHED'}:
            return {'FINISHED'}
        if status == {'CANCELLED'}:
            return {'CANCELLED'}

        scene = context.scene

        # change bounding object settings
        if event.type == 'P' and event.value == 'RELEASE':
            scene.my_use_modifier_stack = not scene.my_use_modifier_stack
            self.execute(context)

        return {'RUNNING_MODAL'}

    def execute(self, context):
        scene = context.scene

        self.obj_mode = context.object.mode

        self.remove_objects(self.new_colliders_list)
        self.new_colliders_list = []

        # reset previously stored displace modifiers when creating a new object
        self.displace_modifiers = []

        # Add the active object to selection if it's not selected. This fixes the rare case when the active Edit mode object is not selected in Object mode.
        if context.object not in self.selected_objects:
            self.selected_objects.append(context.object)
        if not context.object:
            context.view_layer.objects.active = self.selected_objects[0]

        # Create the bounding geometry, depending on edit or object mode.
        obj_amount = len(self.selected_objects)
        old_objs = set(context.scene.objects)

        target_objects = []
        edit_mode = True

        if self.obj_mode == "EDIT":
            bpy.ops.mesh.duplicate_move(MESH_OT_duplicate=None, TRANSFORM_OT_translate=None)
            bpy.ops.mesh.separate(type='SELECTED')

        else: # self.obj_mode == "OBJECT":
            for i, obj in enumerate(self.selected_objects):

                # skip if invalid object
                if obj is None:
                    continue

                # skip non Mesh objects like lamps, curves etc.
                if obj.type != "MESH":
                    continue

                context.view_layer.objects.active = obj

                if self.obj_mode == "OBJECT":
                    bpy.ops.object.duplicate_move(OBJECT_OT_duplicate=None, TRANSFORM_OT_translate=None)

        target_objects=set(context.scene.objects) - old_objs

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        for i, obj in enumerate(target_objects):

            #setup
            bpy.ops.object.mode_set(mode='OBJECT')
            obj.select_set(True)

            context.view_layer.objects.active = obj
            collections = obj.users_collection

            prefs = context.preferences.addons["CollisionHelpers"].preferences
            type_suffix = prefs.boxColSuffix

            new_name = super().collider_name(context, type_suffix, i+1)

            new_collider = obj
            new_collider.name = new_name

            context.view_layer.objects.active = new_collider

            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.convex_hull()
            bpy.ops.object.mode_set(mode='OBJECT')

            # create collision meshes
            # self.custom_set_parent(context, obj, new_collider)

            remove_all_modifiers(new_collider)
            # save collision objects to delete when canceling the operation
            # self.previous_objects.append(new_collider)
            self.primitive_postprocessing(context, new_collider, self.physics_material_name)
            self.add_to_collections(new_collider, collections)

            print('Generated collisions %d/%d' % (i, obj_amount))

        self.new_colliders_list = set(context.scene.objects) - old_objs
        print("New_Collider_List" + str(self.new_colliders_list))

        return {'RUNNING_MODAL'}
