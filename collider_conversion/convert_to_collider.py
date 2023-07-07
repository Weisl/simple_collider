import bpy
from bpy.types import Operator

from ..collider_shapes.add_bounding_primitive import OBJECT_OT_add_bounding_object
default_shape = 'box_shape'
default_group = 'USER_01'


class OBJECT_OT_convert_to_collider(OBJECT_OT_add_bounding_object, Operator):
    """Convert existing objects to be a collider"""
    bl_idname = "object.convert_to_collider"
    bl_label = "Object to Collider"
    bl_description = 'Convert selected meshes to colliders'

    @classmethod
    def poll(cls, context):
        # Convert is only supported in object mode
        return False if context.mode != 'OBJECT' else super().poll(context)

    def __init__(self):
        super().__init__()
        self.is_mesh_to_collider = True

        self.use_shape_change = True
        self.use_decimation = True
        self.shape = 'mesh_shape'
        self.use_keep_original_materials = True
        self.use_keep_original_name = True
        self.use_modifier_stack = True

    def invoke(self, context, event):
        super().invoke(context, event)

        self.use_creation_mode = True
        self.creation_mode = ['INDIVIDUAL', 'SELECTION']
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

        if event.type == 'P' and event.value == 'RELEASE':
            self.my_use_modifier_stack = not self.my_use_modifier_stack
            self.execute(context)

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

        # list of coller
        collider_data = []
        # user collections of the objs
        user_collections = []
        # tmp collection for base objs
        base_collections = [self.create_collection('base_obj')]

        # get list of objects to be converted
        objs = self.get_pre_processed_mesh_objs(context, default_world_spc=False, use_mesh_copy=True)

        for base_ob, obj in objs:

            new_collider = obj
            user_collections = base_ob.users_collection
            bpy.context.collection.objects.link(new_collider)

            # Assign base obj to base object collection
            self.set_collections(base_ob, base_collections)

            # naming
            prefs = context.preferences.addons[__package__.split('.')[0]].preferences

            if self.keep_original_name:
                basename = base_ob.name
            else:
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

        creation_mode = self.creation_mode[self.creation_mode_idx] if self.obj_mode == 'OBJECT' else self.creation_mode_edit[self.creation_mode_idx]

        if creation_mode in ['INDIVIDUAL', 'LOOSEMESH']:
            for mesh_collider_data in collider_data:
                basename = mesh_collider_data['basename']
                new_collider = mesh_collider_data['new_collider']

                self.primitive_postprocessing(context, new_collider, user_collections)
                self.new_colliders_list.append(new_collider)

                if not self.keep_original_name:
                    super().set_collider_name(new_collider, basename)

        else: # self.creation_mode[self.creation_mode_idx] == 'SELECTION':
            # Deselect all objects
            for obj in bpy.data.objects: obj.select_set(False)

            # Select mesh objs
            for mesh_collider_data in collider_data:
                basename = mesh_collider_data['basename']
                new_collider = mesh_collider_data['new_collider']
                new_collider.select_set(True)

            context.view_layer.objects.active = new_collider
            bpy.ops.object.join()

            self.primitive_postprocessing(context, new_collider, user_collections)
            self.new_colliders_list.append(new_collider)

            if not self.keep_original_name:
                super().set_collider_name(new_collider, basename)


        elapsed_time = self.get_time_elapsed()
        super().print_generation_time("Convert to Collider", elapsed_time)
        self.report({'INFO'}, f"Convert to Collider: {float(elapsed_time)}")

        return {'RUNNING_MODAL'}


