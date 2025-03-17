import bpy
from bpy.types import Operator

from .. import __package__ as base_package
from ..collider_shapes.add_bounding_primitive import OBJECT_OT_add_bounding_object

default_shape = 'box_shape'
default_group = 'USER_01'


class OBJECT_OT_convert_to_collider(OBJECT_OT_add_bounding_object, Operator):
    """Convert existing objects to be a collider"""
    bl_idname = "object.convert_to_collider"
    bl_label = "Object to Collider"
    bl_description = 'Convert selected meshes to colliders'

    @staticmethod
    def store_init_state(obj, name, user_collections):
        obj['original_collections'] = obj.get('original_collections') if obj.get(
            'original_collections') else user_collections
        obj['original_name'] = obj.get('original_name') if obj.get('original_name') else name

    @classmethod
    def poll(cls, context):
        # Convert is only supported in object mode
        return False if context.mode != 'OBJECT' else super().poll(context)

    def cancel_cleanup(self, context, **kwargs):
        print('base_objs = ' + str(self.base_objs))
        for obj in self.base_objs:
            obj.hide_set(False)
            if obj.get('original_name'):
                name = obj.get('original_name')
            else:
                name = obj.name

            if obj.get('original_collections'):
                user_collections = obj.get('original_collections')
            else:
                user_collections = obj.users_collection

            obj.name = name
            self.set_collections(obj, user_collections)

        if self.new_colliders_list:
            self.remove_objects(self.new_colliders_list)

        return super().cancel_cleanup(context, delete_colliders=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

        self.shape = self.collider_shapes[self.collider_shapes_idx]
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel_cleanup(context)
            return {'CANCELLED'}
        # apply operator
        elif event.type in {'LEFTMOUSE', 'NUMPAD_ENTER', 'RET'}:
            if self.prefs.debug == False:
                self.remove_objects(self.base_objs)
                self.remove_empty_collection('base_obj')

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

        return {'RUNNING_MODAL'}

    def execute(self, context):
        # CLEANUP and INIT
        super().execute(context)

        # list of collider
        collider_data = []
        # user collections of the objs
        user_collections = []
        # tmp collection for base objs
        base_collections = [self.create_collection('base_obj')]
        self.base_objs = []

        # get list of objects to be converted
        objs = self.get_pre_processed_mesh_objs(context, default_world_spc=False, use_mesh_copy=True,
                                                add_to_tmp_meshes=False)

        for base_ob, obj in objs:

            new_collider = obj
            new_mesh = self.mesh_from_selection(obj, use_modifiers=self.my_use_modifier_stack)
            new_collider.data = new_mesh

            self.store_init_state(base_ob, base_ob.name, base_ob.users_collection)
            self.base_objs.append(base_ob)

            user_collections = base_ob['original_collections']
            bpy.context.collection.objects.link(new_collider)

            # Assign base obj to base object collection
            self.set_collections(base_ob, base_collections)

            original_name = base_ob.get('original_name')

            if base_ob.name == original_name:
                base_ob.name = base_ob.name + '_tmp'
            base_ob.hide_set(True)
            # naming
            prefs = context.preferences.addons[base_package].preferences

            print('original name = ' + original_name)

            if self.keep_original_name:
                basename = original_name
            else:
                if prefs.replace_name:
                    basename = prefs.obj_basename
                elif obj.parent:
                    basename = obj.parent.name
                else:
                    basename = original_name

            mesh_collider_data = {}
            mesh_collider_data['basename'] = basename
            mesh_collider_data['new_collider'] = new_collider
            collider_data.append(mesh_collider_data)

        creation_mode = self.creation_mode[self.creation_mode_idx] if self.obj_mode == 'OBJECT' else \
            self.creation_mode_edit[self.creation_mode_idx]


        if creation_mode in ['INDIVIDUAL'] or self.use_loose_mesh:

            for mesh_collider_data in collider_data:
                basename = mesh_collider_data['basename']
                new_collider = mesh_collider_data['new_collider']

                self.remove_all_modifiers(context, new_collider)
                self.primitive_postprocessing(context, new_collider, user_collections)
                self.new_colliders_list.append(new_collider)

                if self.keep_original_name:
                    new_collider.name = basename
                else:
                    super().set_collider_name(new_collider, basename)

        else:  # self.creation_mode[self.creation_mode_idx] == 'SELECTION':
            # Deselect all objects
            for obj in bpy.data.objects: obj.select_set(False)

            # Select mesh objs
            for mesh_collider_data in collider_data:
                basename = mesh_collider_data['basename']
                new_collider = mesh_collider_data['new_collider']
                new_collider.select_set(True)

            context.view_layer.objects.active = new_collider
            bpy.ops.object.join()

            self.remove_all_modifiers(context, new_collider)
            self.primitive_postprocessing(context, new_collider, user_collections)
            self.new_colliders_list.append(new_collider)

            if self.keep_original_name:
                new_collider.name = basename
            else:
                super().set_collider_name(new_collider, basename)

        elapsed_time = self.get_time_elapsed()
        super().print_generation_time("Convert to Collider", elapsed_time)
        self.report({'INFO'}, f"Convert to Collider: {float(elapsed_time)}")

        return {'RUNNING_MODAL'}
