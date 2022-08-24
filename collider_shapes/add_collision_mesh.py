import bpy
from bpy.types import Operator

from .add_bounding_primitive import OBJECT_OT_add_bounding_object


class OBJECT_OT_add_mesh_collision(OBJECT_OT_add_bounding_object, Operator):
    """Create a new bounding box object"""
    bl_idname = "mesh.add_mesh_collision"
    bl_label = "Add Mesh"
    bl_description = 'Create triangle mesh colliders based on the selection'

    def __init__(self):
        super().__init__()
        self.use_decimation = True
        self.use_modifier_stack = True

    def invoke(self, context, event):
        super().invoke(context, event)
        self.shape_suffix = self.prefs.mesh_shape_identifier
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        status = super().modal(context, event)
        if status == {'FINISHED'}:
            return {'FINISHED'}
        if status == {'CANCELLED'}:
            return {'CANCELLED'}
        if status == {'PASS_THROUGH'}:
            return {'PASS_THROUGH'}
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

        collider_data = []

        for obj in self.selected_objects:

            # skip if invalid object
            if obj is None:
                continue

            # skip non Mesh objects like lamps, curves etc.
            if obj.type != "MESH":
                continue

            mesh_collider_data = {}

            if self.obj_mode == "EDIT":
                new_mesh = self.get_mesh_Edit(obj, use_modifiers=self.my_use_modifier_stack)
                new_collider = bpy.data.objects.new("", new_mesh)

            else:  # mode == "OBJECT":
                new_mesh = self.mesh_from_selection(obj, use_modifiers=self.my_use_modifier_stack)
                new_collider = obj.copy()
                new_collider.data = new_mesh

            if new_mesh == None:
                continue

            scene = context.scene
            mesh_collider_data['parent'] = obj
            mesh_collider_data['new_collider'] = new_collider
            collider_data.append(mesh_collider_data)

        bpy.ops.object.mode_set(mode='OBJECT')

        # Create new collider objects
        for mesh_collider_data in collider_data:
            parent = mesh_collider_data['parent']
            new_collider = mesh_collider_data['new_collider']

            context.scene.collection.objects.link(new_collider)
            self.shape_suffix = self.prefs.mesh_shape_identifier

            # create collision meshes
            self.custom_set_parent(context, parent, new_collider)
            self.remove_all_modifiers(context, new_collider)

            from .add_bounding_primitive import alignObjects
            alignObjects(new_collider, parent)

            new_name = super().collider_name(basename=parent.name)
            new_collider.name = new_name
            new_collider.data.name = new_name + self.data_suffix
            new_collider.data.name = new_name + self.data_suffix

            # save collision objects to delete when canceling the operation
            collections = parent.users_collection

            self.primitive_postprocessing(context, new_collider, collections)
            self.new_colliders_list.append(new_collider)

        # Merge all collider objects
        if self.creation_mode[self.creation_mode_idx] == 'SELECTION':
            bpy.ops.object.select_all(action='DESELECT')
            new_collider = None

            for obj in self.new_colliders_list:
                obj.select_set(True)
                context.view_layer.objects.active = obj
                new_collider = obj

            bpy.ops.object.join()
            self.new_colliders_list = [new_collider]

        # Initial state has to be restored for the modal operator to work. If not, the result will break once changing the parameters
        super().reset_to_initial_state(context)
        super().print_generation_time("Mesh Collider")

        return {'RUNNING_MODAL'}