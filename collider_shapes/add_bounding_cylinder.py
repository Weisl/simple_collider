import bpy
from bpy.types import Operator
from math import sqrt, radians
from mathutils import Vector

from .add_bounding_primitive import OBJECT_OT_add_bounding_object

tmp_name = 'cylindrical_collider'


def calc_hypothenuse(a, b):
    """calculate the hypothenuse"""
    return sqrt((a * 0.5) ** 2 + (b * 0.5) ** 2)


class OBJECT_OT_add_bounding_cylinder(OBJECT_OT_add_bounding_object, Operator):
    """Create cylindrical bounding collisions based on the selection"""
    bl_idname = "mesh.add_bounding_cylinder"
    bl_label = "Add Cylinder"
    bl_description = 'Create cylindrical bounding colliders based on the selection'

    def generate_dimensions_WS(self, v_co):

        positionsX, positionsY, positionsZ = self.split_coordinates_xyz(v_co)

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

    def generate_cylinder_object(self, context, radius, depth, location, rotation_euler=False):
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
                                            calc_uvs=True, )

        new_collider = context.object
        new_collider.name = tmp_name

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

        # cylinder specific
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
        self.shape_suffix = self.prefs.convex_shape_identifier

        collider_data = []
        verts_co = []

        for obj in context.selected_objects.copy():

            # skip if invalid object
            if obj is None:
                continue

            # skip non Mesh objects like lamps, curves etc.
            if obj.type != "MESH":
                continue

            bounding_cylinder_data = {}

            if self.obj_mode == 'EDIT':
                used_vertices = self.get_vertices_Edit(obj, use_modifiers=self.my_use_modifier_stack)
            else:
                used_vertices = self.get_vertices_Object(obj, use_modifiers=self.my_use_modifier_stack)

            if self.creation_mode[self.creation_mode_idx] == 'INDIVIDUAL':
                v_co = self.get_point_positions(obj, scene.my_space, used_vertices)

                dimensions = self.generate_dimensions_WS(v_co)
                bounding_box = self.generate_bounding_box(v_co)

                radius, depth = self.generate_radius_depth(dimensions)

                bounding_cylinder_data['parent'] = obj
                bounding_cylinder_data['radius'] = radius
                bounding_cylinder_data['depth'] = depth
                bounding_cylinder_data['bbox'] = bounding_box
                collider_data.append(bounding_cylinder_data)

            else:  # if self.creation_mode[self.creation_mode_idx] == 'SELECTION':
                # get list of all vertex coordinates in global space
                ws_vtx_co = self.get_point_positions(obj, 'GLOBAL', used_vertices)
                verts_co = verts_co + ws_vtx_co

        if self.creation_mode[self.creation_mode_idx] == 'SELECTION':
            if scene.my_space == 'LOCAL':
                ws_vtx_co = verts_co
                verts_co = self.transform_vertex_space(ws_vtx_co, self.active_obj)

            dimensions = self.generate_dimensions_WS(verts_co)
            bounding_box = self.generate_bounding_box(verts_co)
            radius, depth = self.generate_radius_depth(dimensions)

            bounding_cylinder_data['parent'] = self.active_obj
            bounding_cylinder_data['radius'] = radius
            bounding_cylinder_data['depth'] = depth
            bounding_cylinder_data['bbox'] = bounding_box
            collider_data = [bounding_cylinder_data]

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

            else:  # scene.my_space == 'GLOBAL'
                center = sum((Vector(b) for b in bbox), Vector()) / 8.0
                new_collider = self.generate_cylinder_object(context, radius, depth, center)

            self.new_colliders_list.append(new_collider)
            collections = parent.users_collection
            self.primitive_postprocessing(context, new_collider, collections)

            new_name = super().collider_name(basename=parent.name)
            new_collider.name = new_name
            new_collider.data.name = new_name + self.data_suffix
            new_collider.data.name = new_name + self.data_suffix

            self.custom_set_parent(context, parent, new_collider)

        super().reset_to_initial_state(context)
        super().print_generation_time("Convex Cylindrical Collider")
        return {'RUNNING_MODAL'}
