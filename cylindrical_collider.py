import bmesh
import bpy
from bpy.props import (
    BoolProperty,
    BoolVectorProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
)
from bpy.props import FloatVectorProperty
from bpy.types import Operator
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector

from .utils import alignObjects, getBoundingBox, setOriginToCenterOfMass


def generate_cylinder_Collider_Objectmode(context, my_cylinder_axis):
    """Create cylindrical collider for every selected object in object mode"""
    prefs = bpy.context.preferences.addons[__package__].preferences
    colSuffix = prefs.colSuffix
    colPreSuffix = prefs.colPreSuffix
    convexColSuffix = prefs.convexColSuffix


    activeObject = bpy.context.object
    selectedObjects = bpy.context.selected_objects.copy()
    colliderOb = []

    for i, obj in enumerate(selectedObjects):
        values = [context.object.dimensions[0], context.object.dimensions[1], context.object.dimensions[2]]

        if my_cylinder_axis == 'X':
            radius = max(context.object.dimensions[1], context.object.dimensions[2])*0.5
            depth = context.object.dimensions[0]
        elif my_cylinder_axis == 'Y':
            radius = max(context.object.dimensions[0], context.object.dimensions[2])*0.5
            depth = context.object.dimensions[1]
        else:
            radius = max(context.object.dimensions[0], context.object.dimensions[1])*0.5
            depth = context.object.dimensions[2]

        values = [context.object.dimensions[0], context.object.dimensions[1], context.object.dimensions[2]]

        bpy.ops.mesh.primitive_cylinder_add(vertices=12,
                                            radius=radius,
                                            depth=depth)

        newCollider = bpy.context.object
        newCollider.name = obj.name + colPreSuffix + convexColSuffix + colSuffix

        # centre =  sum((Vector(b) for b in obj.bound_box), Vector())
        # print ('CENTRE' + str(centre))
        # centre /= 8
        # print ('CENTRE 2 ' + str(centre))
        # newCollider.matrix_world = obj.matrix_world * (1 / 8 *

        alignObjects(newCollider, obj)


class OBJECT_OT_add_cylinder_per_object_collision(Operator, AddObjectHelper):
    """Create a new Mesh Object"""
    bl_idname = "mesh.add_cylinder_per_object_collision"
    bl_label = "Add Cylinder Collision Ob"
    bl_options = {'REGISTER', 'UNDO'}

    my_cylinder_axis: EnumProperty(
        name="Axis",
        items=(
            ('X', "X", "X"),
            ('Y', "Y", "Y"),
            ('Z', "Z", "Z"),
        ),
    )

    def execute(self, context):
        generate_cylinder_Collider_Objectmode(context, self.my_cylinder_axis)
        return {'FINISHED'}
