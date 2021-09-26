from math import sqrt

import bpy
from bpy.props import (
    IntProperty,
)
from bpy.types import Operator
from mathutils import Vector

from .add_bounding_primitive import OBJECT_OT_add_bounding_object

def calc_hypothenuse(a, b):
    """calculate the hypothenuse"""
    return sqrt((a * 0.5) ** 2 + (b * 0.5) ** 2)


def generate_cylinder_Collider_Objectmode(self, context, base_object, new_name):
    """Create cylindrical collider for every selected object in object mode
    base_object contains a blender object
    name_suffix gets added to the newly created object name
    """

    if self.cylinder_axis == 'X':
        radius = calc_hypothenuse(base_object.dimensions[1], base_object.dimensions[2])
        depth = base_object.dimensions[0]

    elif self.cylinder_axis == 'Y':
        radius = calc_hypothenuse(base_object.dimensions[0], base_object.dimensions[2])
        depth = base_object.dimensions[1]

    else:
        radius = calc_hypothenuse(base_object.dimensions[0], base_object.dimensions[1])
        depth = base_object.dimensions[2]

    # add new cylindrical mesh
    bpy.ops.mesh.primitive_cylinder_add(vertices=self.vertex_count,
                                        radius=radius,
                                        depth=depth)

    newCollider = context.object
    newCollider.name = new_name

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

    # Defines the resolution of the bounding cylinder
    vertex_count: IntProperty(
        name="Vertices",
        default=8
    )

    def __init__(self):
        super().__init__()
        self.vertex_count = 12
        self.use_vertex_count = True

    def invoke(self, context, event):
        super().invoke(context, event)

        prefs = context.preferences.addons["CollisionHelpers"].preferences
        # collider type specific
        self.type_suffix = prefs.convexColSuffix

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        status = super().modal(context, event)
        if status == {'FINISHED'}:
            return {'FINISHED'}
        if status == {'CANCELLED'}:
            return {'CANCELLED'}

        scene = context.scene

        # change bounding object settings
        if event.type == 'G' and event.value == 'RELEASE':
            scene.my_space = 'GLOBAL'
            self.execute(context)

        elif event.type == 'L' and event.value == 'RELEASE':
            scene.my_space = 'LOCAL'
            self.execute(context)

        # define cylinder axis
        elif event.type == 'X' or event.type == 'Y' or event.type == 'Z' and event.value == 'RELEASE':
            self.cylinder_axis = event.type
            self.execute(context)

        return {'RUNNING_MODAL'}

    def execute(self, context):


        matName = self.physics_material_name

        for i, obj in enumerate(context.selected_objects.copy()):
            # skip if invalid object
            if obj is None:
                continue

            # skip non Mesh objects like lamps, curves etc.
            if obj.type != "MESH":
                continue

            prefs = context.preferences.addons["CollisionHelpers"].preferences
            type_suffix = prefs.boxColSuffix
            new_name = super().collider_name(context, type_suffix, i+1)

            newCollider = generate_cylinder_Collider_Objectmode(self, context, obj, new_name)
            self.primitive_postprocessing(context, newCollider, matName)

        return {'FINISHED'}
