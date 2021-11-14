import bmesh
import bpy
from bpy.types import Operator

from .add_bounding_primitive import OBJECT_OT_add_bounding_object

class OBJECT_OT_add_convex_hull(OBJECT_OT_add_bounding_object, Operator):
    """Create convex bounding collisions based on the selection"""
    bl_idname = "mesh.add_bounding_convex_hull"
    bl_label = "Add Convex Hull"
    bl_description = 'Create convex bounding collisions based on the selection'

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
            self.my_use_modifier_stack = not self.my_use_modifier_stack
            self.execute(context)

        return {'RUNNING_MODAL'}

    def execute(self, context):
        # CLEANUP
        super().execute(context)

        target_objects = []
        self.type_suffix = self.prefs.convexColSuffix

        # Duplicate original meshes to convert to collider
        for obj in self.selected_objects:
            # skip if invalid object
            if obj is None:
                continue

            # skip non Mesh objects like lamps, curves etc.
            if obj.type != "MESH":
                continue

            collider_data = {}

            # update mesh when changing selection in edit mode etc.
            obj.update_from_editmode()

            # duplicate object
            new_collider = obj.copy()
            new_collider.data = obj.data.copy()

            context.scene.collection.objects.link(new_collider)

            if self.obj_mode == "OBJECT":
                self.custom_set_parent(context, obj, new_collider)

            else: #self.obj_mode == 'EDIT'
                bpy.ops.object.mode_set(mode='OBJECT')
                self.custom_set_parent(context, obj, new_collider)

            if self.my_use_modifier_stack:
                self.apply_all_modifiers(context, new_collider)

            obj.select_set(False)

            collider_data['parent'] = obj
            collider_data['convex_collider'] = new_collider

            target_objects.append(collider_data)

        for collider_data in target_objects:

            parent = collider_data['parent']
            new_collider = collider_data['convex_collider']

            new_collider.select_set(True)
            context.view_layer.objects.active = new_collider

            if self.obj_mode == "EDIT":
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='INVERT')
                bpy.ops.mesh.delete(type='FACE')

            else:
                bpy.ops.object.mode_set(mode='EDIT')

            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.convex_hull()
            bpy.ops.object.mode_set(mode='OBJECT')

            self.remove_all_modifiers(context, new_collider)
            # save collision objects to delete when canceling the operation
            # self.previous_objects.append(new_collider)
            collections = parent.users_collection
            self.primitive_postprocessing(context, new_collider, collections)

            new_collider.name = super().collider_name(basename=new_collider.parent.name)

        self.new_colliders_list = set(context.scene.objects) - self.old_objs

        # Initial state has to be restored for the modal operator to work. If not, the result will break once changing the parameters
        super().reset_to_initial_state(context)

        return {'RUNNING_MODAL'}
