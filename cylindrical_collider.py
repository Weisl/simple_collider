import bmesh
import bpy
from bpy.props import (
    BoolProperty,
    BoolVectorProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
)
from bpy.props import FloatVectorProperty
from bpy.types import Operator
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from math import sqrt
from mathutils import Vector

from .utils import alignObjects, getBoundingBox, setOriginToCenterOfMass, setColliderSettings

#TODO: in Edit mode: Create a new object instead of adding it to current object
#TODO: Support spaces
#TODO: Moves base mesh when creating collision in edit mode
#TODO: Cylindrical collisions are not alligned correctly when switching Axis from Z to any other
#TODO: Algorithm for cylindrical collision creation is really bad right now. It takes the diagonale of the bounding box to calculate the cylinder radius.
#TODO: Option for elipse instead of circle profile

def calc_hypothenuse(a, b):
    return sqrt((a * 0.5) ** 2 + (b * 0.5) ** 2)


def generate_cylinder_Collider_Objectmode(self, context, obj, nameSuf):
    """Create cylindrical collider for every selected object in object mode"""
    values = [obj.dimensions[0], obj.dimensions[1], obj.dimensions[2]]

    if self.my_cylinder_axis == 'X':
        radius = calc_hypothenuse(obj.dimensions[1], obj.dimensions[2])
        depth = obj.dimensions[0]

    elif self.my_cylinder_axis == 'Y':
        radius = calc_hypothenuse(obj.dimensions[0], obj.dimensions[2])
        depth = obj.dimensions[1]

    else:
        radius = calc_hypothenuse(obj.dimensions[0], obj.dimensions[1])
        depth = obj.dimensions[2]

    bpy.ops.mesh.primitive_cylinder_add(vertices=self.my_vertex_count,
                                        radius=radius,
                                        depth=depth)

    newCollider = bpy.context.object
    newCollider.name = obj.name + nameSuf

    # local_bbox_center = 1/8 * sum((Vector(b) for b in obj.bound_box), Vector())
    centreBase = sum((Vector(b) for b in obj.bound_box), Vector())/8.0
    global_bbox_center = obj.matrix_world @ centreBase
    # print ('CENTRE' + str(centreBase))
    # centreBase /= 8
    # print ('CENTRE 2 ' + str(centreBase))
    # newCollider.location = centreBase

    print ('CENTRE 2 ' + str(global_bbox_center))
    newCollider.location = global_bbox_center
    newCollider.rotation_euler = obj.rotation_euler
    # alignObjects(newCollider, obj)

    return newCollider


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
        default = 'Z'
    )

    my_collision_shading_view: EnumProperty(
        name="Axis",
        items=(
            ('SOLID', "SOLID", "SOLID"),
            ('WIRE', "WIRE", "WIRE"),
            ('BOUNDS', "BOUNDS", "BOUNDS"),
        )
    )

    my_offset: FloatProperty(
        name="Offset",
        default=0.0
    )

    my_vertex_count: IntProperty(
        name="Vertices",
        default=8
    )

    my_color: bpy.props.FloatVectorProperty(
        name="Collision Color", description="", default=(0.36, 0.5, 1, 0.25),min=0.0, max=1.0,
        subtype='COLOR', size=4
    )

    def execute(self, context):
        prefs = bpy.context.preferences.addons[__package__].preferences
        colSuffix = prefs.colSuffix
        colPreSuffix = prefs.colPreSuffix
        convexColSuffix = prefs.convexColSuffix

        nameSuf = colPreSuffix + convexColSuffix + colSuffix

        for i, obj in enumerate(context.selected_objects.copy()):
            newCollider = generate_cylinder_Collider_Objectmode(self, context,obj,nameSuf)
            setColliderSettings(self, context, newCollider)

        return {'FINISHED'}
