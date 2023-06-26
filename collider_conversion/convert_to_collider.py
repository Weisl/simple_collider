import bpy
from bpy.types import Operator

from ..collider_shapes.add_bounding_primitive import OBJECT_OT_add_bounding_object
default_shape = 'box_shape'
default_group = 'USER_01'


class OBJECT_OT_convert_to_collider(OBJECT_OT_add_bounding_object, Operator):
    """Convert existing objects to be a collider"""
    bl_idname = "object.convert_to_collider"
    bl_label = "Mesh to Collider"
    bl_description = 'Convert selected meshes to colliders'

    @classmethod
    def poll(cls, context):
        # Convert is only supported in object mode
        return False if context.mode != 'OBJECT' else super().poll(context)

    def __init__(self):
        super().__init__()
        self.use_shape_change = True
        self.use_decimation = True
        self.is_mesh_to_collider = True
        # self.use_creation_mode = False
        self.shape = 'mesh_shape'
        self.use_keep_original_materials = True

    def invoke(self, context, event):
        super().invoke(context, event)

        self.collider_shapes_idx = 3
        self.collider_shapes = ['box_shape', 'sphere_shape', 'capsule_shape', 'convex_shape',
                                'mesh_shape']

        self.shape = self.collider_shapes[self.collider_shapes_idx]

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
            self.shape = self.collider_shapes[self.collider_shapes_idx]
            for collider in self.new_colliders_list:
                if collider:
                    collider['collider_shape'] = self.shape
            self.update_names()

        return {'RUNNING_MODAL'}

    def execute(self, context):
        # CLEANUP and INIT
        super().execute(context)

        collider_data = []
        user_collections = []

        # Create the bounding geometry, depending on edit or object mode.
        for obj in self.selected_objects:

            # skip if invalid object
            if not self.is_valid_object(obj):
                continue
            if obj and obj.type in self.valid_object_types:
                obj = self.convert_to_mesh(context, obj)

            new_collider = obj.copy()
            new_collider.data = obj.data.copy()
            user_collections = obj.users_collection

            # New collider to scene
            bpy.context.collection.objects.link(new_collider)

            # store initial state for operation cancel
            self.original_obj_data.append(self.store_initial_obj_state(obj, user_collections))


            for collection in obj.users_collection:
                collection.objects.unlink(obj)

            prefs = context.preferences.addons[__package__.split('.')[0]].preferences

            if prefs.replace_name:
                basename = prefs.obj_basename
            elif obj.parent:
                basename = obj.parent.name
            else:
                basename = obj.name

            mesh_collider_data = {}
            mesh_collider_data['basename'] = basename
            mesh_collider_data['new_collider'] = new_collider
            collider_data.append(mesh_collider_data)

        if self.creation_mode[self.creation_mode_idx] == 'INDIVIDUAL':
            for mesh_collider_data in collider_data:
                basename = mesh_collider_data['basename']
                new_collider = mesh_collider_data['new_collider']

                self.primitive_postprocessing(context, new_collider, user_collections)
                self.new_colliders_list.append(new_collider)
                super().set_collider_name(new_collider, basename)

        else: # self.creation_mode[self.creation_mode_idx] == 'SELECTION':
            bpy.ops.object.select_all(action='DESELECT')
            last_selected = None
            for mesh_collider_data in collider_data:
                basename = mesh_collider_data['basename']
                new_collider = mesh_collider_data['new_collider']
                new_collider.select_set(True)

            context.view_layer.objects.active = new_collider
            bpy.ops.object.join()

            self.primitive_postprocessing(context, new_collider, user_collections)
            self.new_colliders_list.append(new_collider)
            super().set_collider_name(new_collider, basename)


        elapsed_time = self.get_time_elapsed()
        super().print_generation_time("Convert to Collider", elapsed_time)
        self.report({'INFO'}, f"Convert to Collider: {float(elapsed_time)}")

        return {'RUNNING_MODAL'}


