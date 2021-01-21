import bmesh
import bpy
from bpy.types import Operator
from mathutils import Vector

from .add_bounding_primitive import OBJECT_OT_add_bounding_object


def distance_vec(point1: Vector, point2: Vector):
    """Calculate distance between two points."""
    return (point2 - point1).length


def midpoint(p1, p2):
    return Vector((p1 + p2) / 2)


def create_sphere(pos, diameter):
    # Create an empty mesh and the object.
    mesh = bpy.data.meshes.new('Sphere')
    basic_sphere = bpy.data.objects.new("Sphere", mesh)

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
    bm.free()

    bpy.ops.object.shade_smooth()


class OBJECT_OT_add_bounding_sphere(OBJECT_OT_add_bounding_object, Operator):
    """Create a new bounding box object"""
    bl_idname = "mesh.add_bounding_sphere"
    bl_label = "Add Sphere Collision"

    def invoke(self, context, event):
        super().invoke(context, event)
        # return self.execute(context)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        status = super().modal(context, event)
        if status == {'FINISHED'}:
            return {'FINISHED'}
        if status == {'CANCELLED'}:
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def execute(self, context):
        nameSuf = self.name_suffix
        matName = self.physics_material_name
        base_obj = self.active_obj

        scene = context.scene

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
                me = context.edit_object.data
                if self.bm is None or not self.bm.is_valid:
                    # in edit mode so try make a new bmesh
                    self.bmesh(context)

                vertices = self.get_vertices(obj, preselect_all=False)

                # Get vertices wit min and may values
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

                print("min_x %f, max_x, %f, min_y, %f max_y %f, min_z, %f, max_z, %f" % (
                    min_x.x, max_x.x, min_y.y, max_y.y, min_z.z, max_z.z))

                # calculate distances between min and max of every axis
                dx = distance_vec(Vector((min_x.x, min_x.y, min_x.z)), Vector((max_x.x, max_x.y, max_x.z)))
                dy = distance_vec(Vector(min_y), Vector(max_y))
                dz = distance_vec(Vector(min_z), Vector(max_z))

                print("dx %f, dy, %f, dz %f" % (dx, dy, dz))

                # Generate sphere for biggest distance
                if dx >= dy and dx >= dz:
                    mid_point = midpoint(min_x, max_x)
                    create_sphere(mid_point, dx/2)
                elif dy >= dz:
                    mid_point = midpoint(min_y, max_y)
                    create_sphere(mid_point, dy/2)
                else:
                    mid_point = midpoint(min_z, max_z)
                    create_sphere(mid_point, dz/2)

        return {'RUNNING_MODAL'}
