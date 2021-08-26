import bmesh
import bpy
from bpy.types import Operator

from .add_bounding_primitive import OBJECT_OT_add_bounding_object


# TODO: Remove modifiers

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

    def invoke(self, context, event):
        super().invoke(context, event)

        # collider type specific
        self.use_decimation = True

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        status = super().modal(context, event)
        if status == {'FINISHED'}:
            return {'FINISHED'}
        if status == {'CANCELLED'}:
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def execute(self, context):
        self.remove_objects(self.new_colliders_list)
        self.new_colliders_list = []

        # reset previously stored displace modifiers when creating a new object
        self.displace_modifiers = []

        # Add the active object to selection if it's not selected. This fixes the rare case when the active Edit mode object is not selected in Object mode.
        if context.object not in self.selected_objects:
            self.selected_objects.append(context.object)
            print("selected_objects" + self.selected_objects)
        if not context.object:
            context.view_layer.objects.active = self.selected_objects[0]

        # Create the bounding geometry, depending on edit or object mode.
        obj_amount = len(self.selected_objects)
        old_objs = set(context.scene.objects)

        # bpy.ops.object.mode_set(mode='OBJECT')
        # bpy.ops.object.select_all(action='DESELECT')

        for i, obj in enumerate(self.selected_objects):

            # skip if invalid object
            if obj is None:
                continue

            # skip non Mesh objects like lamps, curves etc.
            if obj.type != "MESH":
                continue

            obj.select_set(True)
            context.view_layer.objects.active = obj
            collections = obj.users_collection

            if self.obj_mode == "EDIT":
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.duplicate_move(MESH_OT_duplicate=None, TRANSFORM_OT_translate=None)

                # If the modifier is ignored. It's more efficient to call the convex hull operator immedialty
                # to avoid switching modes multiple times
                if self.use_modifier_stack == False:
                    bpy.ops.mesh.convex_hull(delete_unused=True, use_existing_faces=False, make_holes=False, join_triangles=True, face_threshold=0.698132, shape_threshold=0.698132, uvs=False, vcols=False, seam=False, sharp=False, materials=False)

                bpy.ops.mesh.separate(type='SELECTED')

            else:  # obj_mode == "OBJECT":
                bpy.ops.object.mode_set(mode='EDIT')

                # Get a BMesh representation
                me = obj.data
                bm = bmesh.from_edit_mesh(me)

                # select all vertices
                self.get_vertices(bm, preselect_all=True)

                bpy.ops.mesh.duplicate_move(MESH_OT_duplicate=None, TRANSFORM_OT_translate=None)
                # If the modifier is ignored. It's more efficient to call the convex hull operator immedialty
                # to avoid switching modes multiple times
                if self.use_modifier_stack == False:
                    bpy.ops.mesh.convex_hull(delete_unused=True, use_existing_faces=False, make_holes=False, join_triangles=True, face_threshold=0.698132, shape_threshold=0.698132, uvs=False, vcols=False, seam=False, sharp=False, materials=False)


                bpy.ops.mesh.separate(type='SELECTED')

            bpy.ops.object.mode_set(mode='OBJECT')

            new_collider = list(set(context.scene.objects) - old_objs)[-1]
            new_collider.name = obj.name + self.name_suffix + "_" + str(i)

            if self.use_modifier_stack:
                context.view_layer.objects.active = new_collider
                apply_all_modifiers(new_collider)
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.convex_hull()
                bpy.ops.object.mode_set(mode='OBJECT')

            # create collision meshes
            self.custom_set_parent(context, obj, new_collider)

            remove_all_modifiers(new_collider)
            # save collision objects to delete when canceling the operation
            # self.previous_objects.append(new_collider)
            self.primitive_postprocessing(context, new_collider, self.physics_material_name)
            self.add_to_collections(new_collider, collections)

            print('Generated collisions %d/%d' % (i, obj_amount))

        self.new_colliders_list = set(context.scene.objects) - old_objs
        print("previous_objects" + str(self.new_colliders_list))

        return {'RUNNING_MODAL'}
