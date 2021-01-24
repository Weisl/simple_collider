import bmesh
import bpy
from bpy.types import Operator
from mathutils import Vector

from .add_bounding_primitive import OBJECT_OT_add_bounding_object

# TODO: Expose segments

def distance_vec(point1: Vector, point2: Vector):
    """Calculate distance between two points."""
    return (point2 - point1).length


def midpoint(p1, p2):
    return (p1 + p2) * 0.5


def create_sphere(pos, diameter, name):
    # Create an empty mesh and the object.
    mesh = bpy.data.meshes.new(name)
    basic_sphere = bpy.data.objects.new(name, mesh)

    # Add the object into the scene.
    bpy.context.collection.objects.link(basic_sphere)

    # Select the newly created object
    bpy.context.view_layer.objects.active = basic_sphere
    basic_sphere.select_set(True)
    basic_sphere.location = pos

    # Construct the bmesh sphere and assign it to the blender mesh.
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, diameter=diameter)
    bm.to_mesh(mesh)
    mesh.update()
    bm.clear()

    bpy.ops.object.shade_smooth()

    return basic_sphere


class OBJECT_OT_add_bounding_sphere(OBJECT_OT_add_bounding_object, Operator):
    """Create a new bounding box object"""
    bl_idname = "mesh.add_bounding_sphere"
    bl_label = "Add Sphere Collision"

    def invoke(self, context, event):
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

        # Create the bounding geometry, depending on edit or object mode.
        for i, obj in enumerate(self.selected_objects):

            # skip if invalid object
            if obj is None:
                continue

            # skip non Mesh objects like lamps, curves etc.
            if obj.type != "MESH":
                continue

            context.view_layer.objects.active = obj
            collections = obj.users_collection

            if obj.mode == "EDIT":
                me = obj.data

                # Get a BMesh representation
                bm = bmesh.from_edit_mesh(me)

                vertices = self.get_vertices(bm, preselect_all=False)

            else:  # mode == "OBJECT":
                context.view_layer.objects.active = obj

                bpy.ops.object.mode_set(mode='EDIT')
                me = obj.data

                # Get a BMesh representation
                bm = bmesh.from_edit_mesh(me)

                vertices = self.get_vertices(bm, preselect_all=True)

            # Get vertices wit min and may values
            # First pass
            for i, vertex in enumerate(vertices):

                # convert to global space
                v = obj.matrix_world @ vertex.co

                # ignore 1. point since it's already saved
                if i == 0:
                    min_x = v
                    max_x = v
                    min_y = v
                    max_y = v
                    min_z = v
                    max_z = v

                # compare points to previous min and max
                # v.co returns mathutils.Vector
                else:
                    min_x = v if v.x < min_x.x else min_x
                    max_x = v if v.x > max_x.x else max_x
                    min_y = v if v.y < min_y.y else min_y
                    max_y = v if v.y > max_y.y else max_y
                    min_z = v if v.z < min_z.z else min_z
                    max_z = v if v.z > max_z.z else max_z

            # calculate distances between min and max of every axis
            dx = distance_vec(min_x, max_x)
            dy = distance_vec(min_y, max_y)
            dz = distance_vec(min_z, max_z)

            # Generate sphere for biggest distance
            mid_point = None
            radius = None

            if dx >= dy and dx >= dz:
                mid_point = midpoint(min_x, max_x)
                radius = dx / 2

            elif dy >= dz:
                mid_point = midpoint(min_y, max_y)
                radius = dy / 2

            else:
                mid_point = midpoint(min_z, max_z)
                radius = dz / 2

            # second pass
            for i, vertex in enumerate(vertices):
                # convert to global space
                v = obj.matrix_world @ vertex.co

                # calculate distance to center to find out if the point is in or outside the sphere
                distance_center_to_v = distance_vec(mid_point, v)

                # point is outside the collision sphere
                if distance_center_to_v > radius:
                    radius = (radius + distance_center_to_v) / 2
                    old_to_new = distance_center_to_v - radius

                    # calculate new_midpoint
                    mid_point = (mid_point * radius + v * old_to_new) / distance_center_to_v

            # create collision meshes
            new_collider = create_sphere(mid_point, radius, obj.name + self.name_suffix + "_" + str(i))
            self.custom_set_parent(context, obj, new_collider)

            # save collision objects to delete when canceling the operation
            self.previous_objects.append(new_collider)
            self.cleanup(context, new_collider, self.physics_material_name)
            self.add_to_collections(new_collider, collections)

        return {'RUNNING_MODAL'}
