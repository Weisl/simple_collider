from math import sqrt, radians

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

    if self.cylinder_axis == 'X':
        newCollider.rotation_euler.rotate_axis("Y", radians(90))
    elif self.cylinder_axis == 'Y':
        newCollider.rotation_euler.rotate_axis("X", radians(90))

    return newCollider


class OBJECT_OT_add_bounding_cylinder(OBJECT_OT_add_bounding_object, Operator):
    """Create a Cylindrical bounding object"""
    bl_idname = "mesh.add_bounding_cylinder"
    bl_label = "Add Cylinder Collision Ob"

    def __init__(self):
        super().__init__()
        self.vertex_count = 12
        self.use_vertex_count = True
        self.use_space = True
        self.use_modifier_stack = True
        self.use_global_local_switches = True
        self.use_cylinder_axis = True

    def invoke(self, context, event):
        super().invoke(context, event)
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

        # change bounding object settings
        if event.type == 'P' and event.value == 'RELEASE':
            scene.my_use_modifier_stack = not scene.my_use_modifier_stack
            self.execute(context)

        return {'RUNNING_MODAL'}

    def execute(self, context):
        # CLEANUP
        super().execute(context)

        for i, obj in enumerate(context.selected_objects.copy()):
            # skip if invalid object
            if obj is None:
                continue

            # skip non Mesh objects like lamps, curves etc.
            if obj.type != "MESH":
                continue

            prefs = context.preferences.addons["CollisionHelpers"].preferences
            type_suffix = prefs.convexColSuffix
            new_name = super().collider_name(context, type_suffix, i+1)

            if obj.mode == "OBJECT":
                new_collider = generate_cylinder_Collider_Objectmode(self, context, obj, new_name)
                self.new_colliders_list.append(new_collider)
                self.custom_set_parent(context, obj, new_collider)
                self.primitive_postprocessing(context, new_collider, self.physics_material_name)

        # Initial state has to be restored for the modal operator to work. If not, the result will break once changing the parameters
        super().reset_to_initial_state(context)

        return {'RUNNING_MODAL'}

