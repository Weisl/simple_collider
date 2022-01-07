import bmesh
import bpy
from bpy.types import Operator

from .add_bounding_primitive import OBJECT_OT_add_bounding_object

class OBJECT_OT_add_mesh_collision(OBJECT_OT_add_bounding_object, Operator):
    """Create a new bounding box object"""
    bl_idname = "mesh.add_mesh_collision"
    bl_label = "Add Mesh Collision"
    bl_description = 'Create triangle mesh collisions based on the selection'

    def __init__(self):
        super().__init__()
        self.use_decimation = True
        self.use_modifier_stack = True

    def invoke(self, context, event):
        super().invoke(context, event)
        self.type_suffix = self.prefs.meshColSuffix
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
        # CLEANUP and INIT
        super().execute(context)

        # Add the active object to selection if it's not selected. This fixes the rare case when the active Edit mode object is not selected in Object mode.
        if context.object not in self.selected_objects:
            self.selected_objects.append(context.object)

        for obj in self.selected_objects:

            # skip if invalid object
            if obj is None:
                continue

            # skip non Mesh objects like lamps, curves etc.
            if obj.type != "MESH":
                continue

            context.view_layer.objects.active = obj
            collections = obj.users_collection

            if self.obj_mode == "EDIT":
                bpy.ops.mesh.duplicate()
                bpy.ops.mesh.separate(type='SELECTED')
                bpy.ops.object.mode_set(mode='OBJECT')
                new_collider = context.scene.objects[-1]

            else:  # mode == "OBJECT":
                new_mesh = self.mesh_from_selection(obj, use_modifiers=self.my_use_modifier_stack)
                new_collider = obj.copy()
                new_collider.data = new_mesh
                context.scene.collection.objects.link(new_collider)
                self.remove_all_modifiers(context, new_collider)

            self.type_suffix = self.prefs.boxColSuffix

            # create collision meshes
            self.custom_set_parent(context, obj, new_collider)

            new_collider.name = super().collider_name(basename=obj.name)

            # save collision objects to delete when canceling the operation
            collections = obj.users_collection

            self.primitive_postprocessing(context, new_collider,collections)

        self.new_colliders_list = set(context.scene.objects) - self.old_objs

        # Initial state has to be restored for the modal operator to work. If not, the result will break once changing the parameters
        super().reset_to_initial_state(context)
        print("Time elapsed: ", str(self.get_time_elapsed()))

        return {'RUNNING_MODAL'}
