from math import sqrt, radians

import bpy, bmesh
from bpy.props import (
    IntProperty,
)
from bpy.types import Operator
from mathutils import Vector

from .add_bounding_primitive import OBJECT_OT_add_bounding_object

tmp_name = 'cylindrical_collider'

def calc_hypothenuse(a, b):
    """calculate the hypothenuse"""
    return sqrt((a * 0.5) ** 2 + (b * 0.5) ** 2)


def generate_cylinder_Collider_Objectmode(self, context, base_object):
    """Create cylindrical collider for every selected object in object mode
    base_object contains a blender object
    name_suffix gets added to the newly created object name
    """
    global tmp_name

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
    newCollider.name = tmp_name

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
        self.use_vertex_count = True
        self.use_space = True
        self.use_modifier_stack = True
        self.use_global_local_switches = True
        self.use_cylinder_axis = True

    def generate_bounding_box(self, positionsX, positionsY, positionsZ):
        # get the min and max coordinates for the bounding box
        verts = [
            (max(positionsX), max(positionsY), min(positionsZ)),
            (max(positionsX), min(positionsY), min(positionsZ)),
            (min(positionsX), min(positionsY), min(positionsZ)),
            (min(positionsX), max(positionsY), min(positionsZ)),
            (max(positionsX), max(positionsY), max(positionsZ)),
            (max(positionsX), min(positionsY), max(positionsZ)),
            (min(positionsX), min(positionsY), max(positionsZ)),
            (min(positionsX), max(positionsY), max(positionsZ)),
        ]
        return verts

    def generate_dimensions_WS(self, positionsX, positionsY, positionsZ):
        dimensions = []
        dimensions.append(abs(max(positionsX) - min(positionsX)))
        dimensions.append(max(positionsY) - min(positionsY))
        dimensions.append(abs(max(positionsZ) - min(positionsZ)))

        return dimensions

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
        scene = context.scene
        # CLEANUP
        super().execute(context)

        target_object_mode = []
        target_edit_mode = []

        if self.obj_mode == 'EDIT':
            for i, obj in enumerate(context.selected_objects.copy()):

                # skip if invalid object
                if obj is None:
                    continue

                # skip non Mesh objects like lamps, curves etc.
                if obj.type != "MESH":
                    continue

                bounding_cylinder_data = {}
                me = obj.data

                if scene.my_use_modifier_stack == False:
                    # Get a BMesh representation
                    me.update()
                    bm = bmesh.from_edit_mesh(me)
                    vertices = [v for v in bm.verts if v.select == True]

                else:  # scene.my_use_modifier_stack == True

                    # Get mesh information with the modifiers applied
                    me.update()
                    depsgraph = bpy.context.evaluated_depsgraph_get()
                    bm = bmesh.new()
                    bm.from_object(obj, depsgraph)
                    bm.verts.ensure_lookup_table()
                    vertices = [v for v in bm.verts if v.select == True]


                positionsX, positionsY, positionsZ = self.get_point_positions(obj, scene.my_space, vertices)

                dimensions = self.generate_dimensions_WS(positionsX, positionsY, positionsZ)
                bounding_box = self.generate_bounding_box(positionsX, positionsY, positionsZ)

                if self.cylinder_axis == 'X':
                    radius = calc_hypothenuse(dimensions[1], dimensions[2])
                    depth = dimensions[0]

                elif self.cylinder_axis == 'Y':
                    radius = calc_hypothenuse(dimensions[0], dimensions[2])
                    depth = dimensions[1]

                else:
                    radius = calc_hypothenuse(dimensions[0], dimensions[1])
                    depth = dimensions[2]

                bounding_cylinder_data['parent'] = obj
                bounding_cylinder_data['radius'] = radius
                bounding_cylinder_data['depth'] = depth
                bounding_cylinder_data['bbox'] = bounding_box
                target_edit_mode.append(bounding_cylinder_data)

        else: #self.obj_mode == 'OBJECT':

            for i, obj in enumerate(context.selected_objects.copy()):
                # skip if invalid object
                if obj is None:
                    continue

                # skip non Mesh objects like lamps, curves etc.
                if obj.type != "MESH":
                    continue

                initial_mod_state = {}

                if scene.my_use_modifier_stack == False:
                    for mod in obj.modifiers:
                        initial_mod_state[mod.name] = mod.show_viewport
                        mod.show_viewport = False
                    context.view_layer.update()

                if scene.my_space == 'LOCAL':
                    new_collider = generate_cylinder_Collider_Objectmode(self, context, obj)

                else:  # Space == 'GLOBAL'
                    # WS_vertives = [obj.matrix_world @ v.co for v in obj.data.vertices]

                    if scene.my_use_modifier_stack == False:
                        vertices = obj.data.vertices

                    if scene.my_use_modifier_stack == True:
                        # Get mesh information with the modifiers applied
                        depsgraph = bpy.context.evaluated_depsgraph_get()
                        bm = bmesh.new()
                        bm.from_object(obj, depsgraph)
                        bm.verts.ensure_lookup_table()
                        vertices = bm.verts

                    positionsX, positionsY, positionsZ = self.get_point_positions(obj, 'GLOBAL', vertices)
                    dimensions = self.generate_dimensions_WS(positionsX, positionsY, positionsZ)
                    bounding_box = self.generate_bounding_box(positionsX, positionsY, positionsZ)

                    if self.cylinder_axis == 'X':
                        radius = calc_hypothenuse(dimensions[1], dimensions[2])
                        depth = dimensions[0]

                    elif self.cylinder_axis == 'Y':
                        radius = calc_hypothenuse(dimensions[0], dimensions[2])
                        depth = dimensions[1]

                    else:
                        radius = calc_hypothenuse(dimensions[0], dimensions[1])
                        depth = dimensions[2]

                    # add new cylindrical mesh
                    bpy.ops.mesh.primitive_cylinder_add(vertices=self.vertex_count,
                                                        radius=radius,
                                                        depth=depth)
                    new_collider = context.object

                    # align newly created object to base mesh
                    centreBase = sum((Vector(b) for b in bounding_box), Vector()) / 8.0
                    global_bbox_center = centreBase
                    new_collider.location = global_bbox_center

                    if self.cylinder_axis == 'X':
                        new_collider.rotation_euler.rotate_axis("Y", radians(90))
                    elif self.cylinder_axis == 'Y':
                        new_collider.rotation_euler.rotate_axis("X", radians(90))

                # Reset modifiers of target mesh to initial state
                if scene.my_use_modifier_stack == False:
                    for mod_name, value in initial_mod_state.items():
                        obj.modifiers[mod_name].show_viewport = value

                target_object_mode.append(new_collider)

        bpy.ops.object.mode_set(mode='OBJECT')

        if self.obj_mode == 'EDIT':
            for bounding_cylinder_data in target_edit_mode:
                global tmp_name

                print(str(bounding_cylinder_data))

                parent = bounding_cylinder_data['parent']
                radius = bounding_cylinder_data['radius']
                depth = bounding_cylinder_data['depth']
                bbox = bounding_cylinder_data['bbox']

                # add new cylindrical mesh
                bpy.ops.mesh.primitive_cylinder_add(vertices=self.vertex_count,
                                                    radius=radius,
                                                    depth=depth)

                new_collider = context.object
                new_collider.name = tmp_name

                # align newly created object to base mesh
                centreBase = sum((Vector(b) for b in bbox), Vector()) / 8.0
                new_collider.location = centreBase

                if scene.my_space == 'LOCAL':
                    new_collider.rotation_euler = parent.rotation_euler

                if self.cylinder_axis == 'X':
                    new_collider.rotation_euler.rotate_axis("Y", radians(90))
                elif self.cylinder_axis == 'Y':
                    new_collider.rotation_euler.rotate_axis("X", radians(90))

                prefs = context.preferences.addons["CollisionHelpers"].preferences
                type_suffix = prefs.convexColSuffix
                new_collider.name = super().collider_name(context, type_suffix, i + 1)

                self.new_colliders_list.append(new_collider)
                self.custom_set_parent(context, obj, new_collider)
                self.primitive_postprocessing(context, new_collider, self.physics_material_name)


        else: #   if obj.mode == 'OBJECT':

            for new_collider in target_object_mode:

                prefs = context.preferences.addons["CollisionHelpers"].preferences
                type_suffix = prefs.convexColSuffix
                new_collider.name = super().collider_name(context, type_suffix, i + 1)

                self.new_colliders_list.append(new_collider)
                self.custom_set_parent(context, obj, new_collider)
                self.primitive_postprocessing(context, new_collider, self.physics_material_name)

        # Initial state has to be restored for the modal operator to work. If not, the result will break once changing the parameters
        super().reset_to_initial_state(context)

        return {'RUNNING_MODAL'}

