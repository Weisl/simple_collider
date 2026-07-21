import bpy
from bpy.types import Operator

from .add_bounding_primitive import OBJECT_OT_add_bounding_object
from ..bmesh_operations.voxel_generation import build_voxel_bmesh, mesh_max_dimension


class OBJECT_OT_add_bounding_voxel(OBJECT_OT_add_bounding_object, Operator):
    """Create a watertight low-poly collider based on a 3D voxel grid"""
    bl_idname = "mesh.add_bounding_voxel"
    bl_label = "Add Voxel"
    bl_description = 'Create a simplified watertight collider based on a 3D voxel grid'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_modifier_stack = True
        # Reused only for the shared "Voxel Size" modal overlay + mouse-drag
        # handling in the base class -- add_remesh_modifier() is overridden
        # below so it doesn't also attach a Remesh modifier.
        self.use_remesh = True
        self.shape = 'voxel_shape'
        self.initial_shape = 'voxel_shape'
        # use_diagonal_fill (set True here) tells the base class's modal
        # overlay to show the "Diagonal Fill (F)" row; diagonal_fill is the
        # actual current on/off state, toggled by the F key below.
        self.use_diagonal_fill = True
        self.diagonal_fill = False

    def invoke(self, context, event):
        return super().invoke(context, event)

    def add_remesh_modifier(self, context, bounding_object):
        pass

    def set_modal_state(self, cylinder_segments_active=False, displace_active=False, decimate_active=False,
                        opacity_active=False, sphere_segments_active=False, capsule_segments_active=False,
                        remesh_active=False, height_active=False, width_active=False):
        super().set_modal_state(cylinder_segments_active, displace_active, decimate_active,
                                opacity_active, sphere_segments_active, capsule_segments_active,
                                remesh_active, height_active, width_active)
        self.remesh_active = remesh_active

    def modal(self, context, event):
        prev_voxel_mult = self.current_settings_dic.get('voxel_size_multiplier')
        status = super().modal(context, event)
        if status == {'FINISHED'}:
            return {'FINISHED'}
        if status == {'CANCELLED'}:
            return {'CANCELLED'}
        if status == {'PASS_THROUGH'}:
            return {'PASS_THROUGH'}

        if event.type == 'R' and event.value == 'RELEASE':
            self.set_modal_state(remesh_active=not self.remesh_active)

        elif event.type == 'F' and event.value == 'RELEASE':
            self.diagonal_fill = not self.diagonal_fill
            self.execute(context)

        elif event.type == 'P' and event.value == 'RELEASE':
            self.my_use_modifier_stack = not self.my_use_modifier_stack
            self.execute(context)

        elif event.type == 'MOUSEMOVE' and self.remesh_active:
            if self.current_settings_dic['voxel_size_multiplier'] != prev_voxel_mult:
                self.execute(context)

        return {'RUNNING_MODAL'}

    def execute(self, context):
        # CLEANUP and INIT
        super().execute(context)

        collider_data = []
        objs = self.get_pre_processed_mesh_objs(context, default_world_spc=False)

        for base_ob, obj in objs:
            if self.obj_mode == "EDIT" and base_ob.type == 'MESH' and self.active_obj.type == 'MESH' and not self.use_loose_mesh:
                new_mesh = self.get_mesh_Edit(obj, use_modifiers=self.my_use_modifier_stack)
            else:  # self.obj_mode == "OBJECT" or self.use_loose_mesh == True
                new_mesh = self.mesh_from_selection(obj, use_modifiers=self.my_use_modifier_stack)

            if new_mesh is None:
                continue

            max_dim = mesh_max_dimension(new_mesh) or 1.0
            voxel_size = self.current_settings_dic['voxel_size_multiplier'] * max_dim

            voxel_bm = build_voxel_bmesh(new_mesh, voxel_size, diagonal_fill=self.diagonal_fill)
            bpy.data.meshes.remove(new_mesh)
            if voxel_bm is None:
                continue

            voxel_mesh = bpy.data.meshes.new("")
            voxel_bm.to_mesh(voxel_mesh)
            voxel_bm.free()

            new_collider = bpy.data.objects.new("", voxel_mesh)

            mesh_collider_data = {
                'parent': base_ob,
                'mtx_world': base_ob.matrix_world.copy(),
                'new_collider': new_collider,
            }
            collider_data.append(mesh_collider_data)

        bpy.context.view_layer.objects.active = self.active_obj
        bpy.ops.object.mode_set(mode='OBJECT')

        for mesh_collider_data in collider_data:
            parent = mesh_collider_data['parent']
            new_collider = mesh_collider_data['new_collider']
            mtx_world = mesh_collider_data['mtx_world']

            context.scene.collection.objects.link(new_collider)
            new_collider.matrix_world = mtx_world
            self.custom_set_parent(context, parent, new_collider)

            self.new_colliders_list.append(new_collider)
            collections = parent.users_collection
            self.primitive_postprocessing(context, new_collider, collections)
            super().set_collider_name(new_collider, parent.name)

        # Merge all collider objects into one per the selected creation mode
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

        if self.join_primitives:
            super().join_primitives(context)

        # Initial state has to be restored for the modal operator to work. If not, the result will break once changing the parameters
        super().reset_to_initial_state(context)
        elapsed_time = self.get_time_elapsed()
        super().print_generation_time("Voxel Collider", elapsed_time)
        self.report({'INFO'}, f"Voxel Collider: {float(elapsed_time)}")

        return {'RUNNING_MODAL'}
