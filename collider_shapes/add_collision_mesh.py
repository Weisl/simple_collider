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
        self.use_weld_modifier = True
        self.use_keep_original_materials = True
        self.shape = "mesh_shape"


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

        # Keep original material is currently not supported for EDIT mode.
        if self.obj_mode != 'OBJECT':
            self.keep_original_material = False

        collider_data = []

        for base_ob in self.selected_objects:

            # skip if invalid object
            if not self.is_valid_object(base_ob):
                continue

            if base_ob and base_ob.type in self.valid_object_types:
                if base_ob.type == 'MESH':
                    obj = base_ob

                else:
                    # store initial state for operation cancel
                    user_collections = base_ob.users_collection
                    self.original_obj_data.append(self.store_initial_obj_state(base_ob, user_collections))
                    # convert meshes
                    obj = self.convert_to_mesh(context, base_ob, use_modifiers=self.my_use_modifier_stack)
                    self.tmp_meshes.append(obj)

            mesh_collider_data = {}

            if self.obj_mode == "EDIT" and base_ob.type == 'MESH' and self.active_obj.type == 'MESH':
                new_mesh = self.get_mesh_Edit(obj, use_modifiers=self.my_use_modifier_stack)
                new_collider = bpy.data.objects.new("", new_mesh)

            else:  # mode == "OBJECT":
                new_mesh = self.mesh_from_selection(obj, use_modifiers=self.my_use_modifier_stack)
                new_collider = obj.copy()
                new_collider.data = new_mesh

            if new_mesh is None:
                continue

            scene = context.scene
            mesh_collider_data['parent'] = base_ob
            mesh_collider_data['new_collider'] = new_collider
            collider_data.append(mesh_collider_data)

        bpy.ops.object.mode_set(mode='OBJECT')

        # Create new collider objects
        for mesh_collider_data in collider_data:
            parent = mesh_collider_data['parent']
            new_collider = mesh_collider_data['new_collider']

            context.scene.collection.objects.link(new_collider)
            self.shape_suffix = self.prefs.mesh_shape

            # create collision meshes
            self.custom_set_parent(context, parent, new_collider)
            self.remove_all_modifiers(context, new_collider)

            # align objects
            new_collider.matrix_world = parent.matrix_world

            super().set_collider_name(new_collider, parent.name)

            # save collision objects to delete when canceling the operation
            collections = parent.users_collection

            self.primitive_postprocessing(context, new_collider, collections)
            self.new_colliders_list.append(new_collider)

        # Merge all collider objects
        if self.creation_mode[self.creation_mode_idx] == 'SELECTION':
            bpy.ops.object.select_all(action='DESELECT')
            last_selected = None

            for obj in self.new_colliders_list:
                if obj:
                    obj.select_set(True)
                    context.view_layer.objects.active = obj
                    last_selected = obj

            bpy.ops.object.join()

            self.new_colliders_list = [last_selected] if last_selected else []

        # Initial state has to be restored for the modal operator to work. If not, the result will break once changing the parameters
        super().reset_to_initial_state(context)
        elapsed_time = self.get_time_elapsed()
        super().print_generation_time("Mesh Collider", elapsed_time)
        self.report({'INFO'}, f"Mesh Collider: {float(elapsed_time)}")

        return {'RUNNING_MODAL'}
