import bmesh
import bpy
from bpy.types import Operator

from .add_bounding_primitive import OBJECT_OT_add_bounding_object


class OBJECT_OT_add_convex_hull(OBJECT_OT_add_bounding_object, Operator):
    """Create a new bounding box object"""
    bl_idname = "mesh.add_bounding_convex_hull"
    bl_label = "Add Convex Hull"

    def invoke(self, context, event):
        self.obj_mode = context.object.mode
        super().invoke(context, event)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        status = super().modal(context, event)
        if status == {'FINISHED'}:
            return {'FINISHED'}
        if status == {'CANCELLED'}:
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def execute(self, context):
        self.remove_objects(self.previous_objects)
        self.previous_objects = []

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

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

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
                bpy.ops.mesh.duplicate()
                bpy.ops.mesh.convex_hull()
                bpy.ops.mesh.separate(type='SELECTED')

            else:  #obj_mode == "OBJECT":
                bpy.ops.object.mode_set(mode='EDIT')

                # Get a BMesh representation
                me = obj.data
                bm = bmesh.from_edit_mesh(me)

                # select all vertices
                self.get_vertices(bm, preselect_all=True)

                bpy.ops.mesh.duplicate()
                bpy.ops.mesh.convex_hull()
                bpy.ops.mesh.separate(type='SELECTED')

                pass

            bpy.ops.object.mode_set(mode='OBJECT')

            new_collider = context.scene.objects[-1]
            new_collider.name = obj.name + self.name_suffix + "_" + str(i)

            # create collision meshes
            self.custom_set_parent(context, obj, new_collider)

            # save collision objects to delete when canceling the operation
            # self.previous_objects.append(new_collider)
            self.cleanup(context, new_collider, self.physics_material_name)
            self.add_to_collections(new_collider, collections)

            print('Generated collisions %d/%d' % (i, obj_amount))

        self.previous_objects = set(context.scene.objects) - old_objs
        print("previous_objects" + str(self.previous_objects))

        return {'RUNNING_MODAL'}
