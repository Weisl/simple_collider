import bpy
from bpy.types import Operator

from .add_bounding_primitive import OBJECT_OT_add_bounding_object
from ..pyshics_materials.material_functions import set_material


class OBJECT_OT_add_remesh_collision(OBJECT_OT_add_bounding_object, Operator):
    """Create a new bounding box object"""
    bl_idname = "mesh.add_remesh_collision"
    bl_label = "Add Re-meshed"
    bl_description = 'Create a triangle mesh colliders based on the voxel re-meshed target'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_decimation = True
        self.use_modifier_stack = True
        self.use_weld_modifier = True
        self.use_keep_original_materials = True
        self.use_remesh = True
        self.shape = "mesh_shape"
        self.initial_shape = "mesh_shape"

    def invoke(self, context, event):
        super().invoke(context, event)
        return {'RUNNING_MODAL'}

    def set_modal_state(self, cylinder_segments_active=False, displace_active=False, decimate_active=False,
                        opacity_active=False, sphere_segments_active=False, capsule_segments_active=False,
                        remesh_active=False, height_active=False, width_active=False):
        super().set_modal_state(cylinder_segments_active, displace_active, decimate_active,
                                opacity_active, sphere_segments_active, capsule_segments_active,
                                remesh_active, height_active, width_active)
        self.remesh_active = remesh_active

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

        # change bounding object settings
        if event.type == 'R' and event.value == 'RELEASE':
            self.set_modal_state(remesh_active=not self.remesh_active)

        return {'RUNNING_MODAL'}

    def execute(self, context):
        # CLEANUP and INIT
        super().execute(context)

        # Add the active object to selection if it's not selected. This fixes the rare case when the active Edit mode object is not selected in Object mode.
        if context.object not in self.selected_objects:
            self.selected_objects.append(context.object)

        collider_data = []
        objs = []

        objs = self.get_pre_processed_mesh_objs(context, default_world_spc=False)

        for base_ob, obj in objs:
            mesh_collider_data = {}

            if self.obj_mode == "EDIT" and base_ob.type == 'MESH' and self.active_obj.type == 'MESH' and not self.use_loose_mesh:
                new_mesh = self.get_mesh_Edit(obj, use_modifiers=self.my_use_modifier_stack)
                new_collider = bpy.data.objects.new("", new_mesh)
                for mat in base_ob.material_slots:
                    set_material(new_collider, mat.material)

            else:  # self.obj_mode  == "OBJECT" or self.use_loose_mesh == True:
                new_mesh = self.mesh_from_selection(obj, use_modifiers=self.my_use_modifier_stack)
                new_collider = obj.copy()
                new_collider.data = new_mesh

            if new_mesh is None:
                continue

            scene = context.scene
            mesh_collider_data['parent'] = base_ob
            mesh_collider_data['mtx_world'] = base_ob.matrix_world.copy()
            mesh_collider_data['new_collider'] = new_collider
            collider_data.append(mesh_collider_data)

        bpy.context.view_layer.objects.active = self.active_obj
        bpy.ops.object.mode_set(mode='OBJECT')

        # Create new collider objects
        for mesh_collider_data in collider_data:
            parent = mesh_collider_data['parent']
            new_collider = mesh_collider_data['new_collider']
            mtx_world = mesh_collider_data['mtx_world']

            context.scene.collection.objects.link(new_collider)
            self.shape_suffix = self.prefs.mesh_shape

            # create collision meshes
            new_collider.matrix_world = mtx_world
            self.custom_set_parent(context, parent, new_collider)
            self.remove_all_modifiers(context, new_collider)

            super().set_collider_name(new_collider, parent.name)

            # save collision objects to delete when canceling the operation
            collections = parent.users_collection

            self.primitive_postprocessing(context, new_collider, collections)
            self.new_colliders_list.append(new_collider)

        # Merge all collider objects
        if self.creation_mode[self.creation_mode_idx] == 'SELECTION' and not self.use_loose_mesh:
            bpy.ops.object.select_all(action='DESELECT')
            last_selected = None

            for obj in self.new_colliders_list:
                if obj:
                    obj.select_set(True)
                    context.view_layer.objects.active = obj
                    last_selected = obj

            bpy.ops.object.join()

            self.new_colliders_list = [last_selected] if last_selected else []

        # Merge all collider objects
        if self.join_primitives:
            super().join_primitives(context)

        # Initial state has to be restored for the modal operator to work. If not, the result will break once changing the parameters
        super().reset_to_initial_state(context)
        elapsed_time = self.get_time_elapsed()
        super().print_generation_time("Mesh Collider", elapsed_time)
        self.report({'INFO'}, f"Mesh Collider: {float(elapsed_time)}")

        return {'RUNNING_MODAL'}
