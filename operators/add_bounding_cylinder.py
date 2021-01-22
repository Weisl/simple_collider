from math import sqrt

import bpy
from bpy.props import (
    EnumProperty,
    IntProperty,
)
from bpy.types import Operator
from mathutils import Vector

from .add_bounding_primitive import OBJECT_OT_add_bounding_object


# TODO: in Edit mode: Create a new object instead of adding it to current object
# TODO: Support spaces
# TODO: Moves base mesh when creating collision in edit mode
# TODO: Cylindrical collisions are not alligned correctly when switching Axis from Z to any other
# TODO: Algorithm for cylindrical collision creation is really bad right now. It takes the diagonale of the bounding box to calculate the cylinder radius.
# TODO: Option for elipse instead of circle profile

def calc_hypothenuse(a, b):
    """calculate the hypothenuse"""
    return sqrt((a * 0.5) ** 2 + (b * 0.5) ** 2)


def generate_cylinder_Collider_Objectmode(self, context, base_object, name_suffix):
    """Create cylindrical collider for every selected object in object mode
    base_object contains a blender object
    name_suffix gets added to the newly created object name
    """

    if self.my_cylinder_axis == 'X':
        radius = calc_hypothenuse(base_object.dimensions[1], base_object.dimensions[2])
        depth = base_object.dimensions[0]

    elif self.my_cylinder_axis == 'Y':
        radius = calc_hypothenuse(base_object.dimensions[0], base_object.dimensions[2])
        depth = base_object.dimensions[1]

    else:
        radius = calc_hypothenuse(base_object.dimensions[0], base_object.dimensions[1])
        depth = base_object.dimensions[2]

    # add new cylindrical mesh
    bpy.ops.mesh.primitive_cylinder_add(vertices=self.my_vertex_count,
                                        radius=radius,
                                        depth=depth)

    newCollider = context.object
    newCollider.name = base_object.name + name_suffix

    # align newly created object to base mesh
    centreBase = sum((Vector(b) for b in base_object.bound_box), Vector()) / 8.0
    global_bbox_center = base_object.matrix_world @ centreBase
    newCollider.location = global_bbox_center
    newCollider.rotation_euler = base_object.rotation_euler

    return newCollider


class OBJECT_OT_add_bounding_cylinder(OBJECT_OT_add_bounding_object, Operator):
    """Create a Cylindrical bounding object"""
    bl_idname = "mesh.add_bounding_cylinder"
    bl_label = "Add Cylinder Collision Ob"

    # defines the orientation of bounding cylinder
    my_cylinder_axis: EnumProperty(
        name="Axis",
        items=(
            ('X', "X", "X"),
            ('Y', "Y", "Y"),
            ('Z', "Z", "Z"),
        ),
        default='Z'
    )

    # Defines the resolution of the bounding cylinder
    my_vertex_count: IntProperty(
        name="Vertices",
        default=8
    )

    def invoke(self, context, event):
        super().invoke(context, event)
        return self.execute(context)

    def execute(self, context):
        nameSuf = self.name_suffix
        matName = self.physics_material_name

        for i, obj in enumerate(context.selected_objects.copy()):
            newCollider = generate_cylinder_Collider_Objectmode(self, context, obj, nameSuf)
            self.cleanup(context, newCollider, matName)

        return {'FINISHED'}
