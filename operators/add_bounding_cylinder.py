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

class OBJECT_OT_add_bounding_cylinder(OBJECT_OT_add_bounding_object, Operator):
    """Create cylindrical bounding collisions based on the selection"""
    bl_idname = "mesh.add_bounding_cylinder"
    bl_label = "Add Cylindrical Collision"
    bl_description = 'Create cylindrical bounding collisions based on the selection'

    def generate_dimensions_WS(self, positionsX, positionsY, positionsZ):
        """Generate the dimenstions based on the 3 lists of positions (X,Y,Z)"""
        dimensions = []
        dimensions.append(abs(max(positionsX) - min(positionsX)))
        dimensions.append(max(positionsY) - min(positionsY))
        dimensions.append(abs(max(positionsZ) - min(positionsZ)))

        return dimensions

    def generate_radius_depth(self, dimensions):
        """Calculate a radiuse based on dimensions and orientations."""
        if self.cylinder_axis == 'X':
            radius = calc_hypothenuse(dimensions[1], dimensions[2])
            depth = dimensions[0]

        elif self.cylinder_axis == 'Y':
            radius = calc_hypothenuse(dimensions[0], dimensions[2])
            depth = dimensions[1]

        else:
            radius = calc_hypothenuse(dimensions[0], dimensions[1])
            depth = dimensions[2]

        return radius, depth

    def generate_cylinder_object(self, context, radius, depth, location, rotation_euler = False):
        """Create cylindrical collider for every selected object in object mode
        base_object contains a blender object
        name_suffix gets added to the newly created object name
        """
        global tmp_name

        # add new cylindrical mesh
        bpy.ops.mesh.primitive_cylinder_add(vertices=self.current_settings_dic['cylinder_segments'],
                                            radius=radius,
                                            depth=depth,
                                            end_fill_type='TRIFAN',
                                            calc_uvs= True,)

        new_collider = context.object
        new_collider.name = tmp_name

        scene=context.scene

        new_collider.location = location

        if rotation_euler:
            new_collider.rotation_euler = rotation_euler

        if self.cylinder_axis == 'X':
            new_collider.rotation_euler.rotate_axis("Y", radians(90))
        elif self.cylinder_axis == 'Y':
            new_collider.rotation_euler.rotate_axis("X", radians(90))

        return new_collider

    def __init__(self):
        super().__init__()
        self.use_space = True
        self.use_modifier_stack = True
        self.use_global_local_switches = True

        #cylinder specific
        self.use_vertex_count = True
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
        if status == {'PASS_THROUGH'}:
            return {'PASS_THROUGH'}
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
            self.my_use_modifier_stack = not self.my_use_modifier_stack
            self.execute(context)

        return {'RUNNING_MODAL'}

    def execute(self, context):
        # CLEANUP
        super().execute(context)

        scene = context.scene
        self.type_suffix = self.prefs.convexColSuffix

        collider_data = []

        for obj in context.selected_objects.copy():

            # skip if invalid object
            if obj is None:
                continue

            # skip non Mesh objects like lamps, curves etc.
            if obj.type != "MESH":
                continue

            bounding_cylinder_data = {}
            me = obj.data

            if self.obj_mode == 'EDIT':
                vertices = self.get_vertices_Edit(obj, use_modifiers=self.my_use_modifier_stack)
            else:
                vertices = self.get_vertices_Object(obj, use_modifiers=self.my_use_modifier_stack)

            positionsX, positionsY, positionsZ = self.get_point_positions(obj, scene.my_space, vertices)
            dimensions = self.generate_dimensions_WS(positionsX, positionsY, positionsZ)
            bounding_box = self.generate_bounding_box(positionsX, positionsY, positionsZ)

            radius, depth = self.generate_radius_depth(dimensions)

            bounding_cylinder_data['parent'] = obj
            bounding_cylinder_data['radius'] = radius
            bounding_cylinder_data['depth'] = depth
            bounding_cylinder_data['bbox'] = bounding_box
            collider_data.append(bounding_cylinder_data)

        bpy.ops.object.mode_set(mode='OBJECT')

        for bounding_cylinder_data in collider_data:
            global tmp_name

            parent = bounding_cylinder_data['parent']
            radius = bounding_cylinder_data['radius']
            depth = bounding_cylinder_data['depth']
            bbox = bounding_cylinder_data['bbox']

            if scene.my_space == 'LOCAL':
                matrix_WS = parent.matrix_world
                center = sum((Vector(matrix_WS @ Vector(b)) for b in bbox), Vector()) / 8.0
                new_collider = self.generate_cylinder_object(context, radius, depth, center,
                                                    rotation_euler=parent.rotation_euler)
                new_collider.scale = parent.scale

            else: # scene.my_space == 'GLOBAL'
                center = sum((Vector(b) for b in bbox), Vector()) / 8.0
                new_collider = self.generate_cylinder_object(context, radius, depth, center)

            self.new_colliders_list.append(new_collider)
            # self.custom_set_parent(context, parent, new_collider)
            collections = parent.users_collection
            self.primitive_postprocessing(context, new_collider, collections)

            new_collider.name = super().collider_name(basename=parent.name)
            self.custom_set_parent(context, parent, new_collider)

        super().reset_to_initial_state(context)
        super().print_generation_time("Convex Cylindrical Collider")
        return {'RUNNING_MODAL'}

