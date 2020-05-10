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


    activeObject = bpy.context.object
    selectedObjects = bpy.context.selected_objects.copy()
    colliderOb = []

    for i, obj in enumerate(selectedObjects):
        values = [context.object.dimensions[0], context.object.dimensions[1], context.object.dimensions[2]]
        bpy.ops.mesh.primitive_cylinder_add(vertices=12,
                                            radius=max(values[0], values[1]) / 2.0,
                                            depth=values[2])

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
            ('X', "x", ""),
            ('Y', "y", ""),
            ('Z', "z", ""),
        ),
    )

    def execute(self, context):
        generate_cylinder_Collider_Objectmode(context, self.my_cylinder_axis)
        return {'FINISHED'}
