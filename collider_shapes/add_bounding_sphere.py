import bmesh
import bpy
from bpy.types import Operator
from mathutils import Vector

from .add_bounding_primitive import OBJECT_OT_add_bounding_object

tmp_sphere_name = 'sphere_collider'


def distance_vec(point1: Vector, point2: Vector):
    """Calculate distance between two points."""
    return (point2 - point1).length


def midpoint(p1, p2):
    return (p1 + p2) * 0.5


def create_sphere(pos, diameter, segments):
    global tmp_sphere_name

    # Create an empty mesh and the object.
    mesh = bpy.data.meshes.new(tmp_sphere_name)
    basic_sphere = bpy.data.objects.new(tmp_sphere_name, mesh)

    # Add the object into the scene.
    bpy.context.collection.objects.link(basic_sphere)

    # Select the newly created object
    bpy.context.view_layer.objects.active = basic_sphere
    basic_sphere.select_set(True)
    basic_sphere.location = pos

    # Construct the bmesh sphere and assign it to the blender mesh.
    bm = bmesh.new()
    if bpy.app.version >= (3, 0, 0):
        bmesh.ops.create_uvsphere(bm, u_segments=segments * 2, v_segments=segments, radius=diameter)
    else:
        bmesh.ops.create_uvsphere(bm, u_segments=segments * 2, v_segments=segments, diameter=diameter)

    for f in bm.faces: f.smooth = True

    bm.to_mesh(mesh)
    mesh.update()
    bm.clear()

    return basic_sphere


class OBJECT_OT_add_bounding_sphere(OBJECT_OT_add_bounding_object, Operator):
    """Create a new bounding box object"""
    bl_idname = "mesh.add_bounding_sphere"
    bl_label = "Add Sphere"
    bl_description = 'Create spherical colliders based on the selection'

    @staticmethod
    def calculate_bounding_sphere(obj, used_vertices):
        # Get vertices wit min and may values
        for i, vertex in enumerate(used_vertices):

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

        # calculate distances between min and max of every axis
        dx = distance_vec(min_x, max_x)
        dy = distance_vec(min_y, max_y)
        dz = distance_vec(min_z, max_z)

        mid_point = None
        radius = None

        # Generate sphere for biggest distance
        if dx >= dy and dx >= dz:
            mid_point = midpoint(min_x, max_x)
            radius = dx / 2

        elif dy >= dz:
            mid_point = midpoint(min_y, max_y)
            radius = dy / 2

        else:
            mid_point = midpoint(min_z, max_z)
            radius = dz / 2

        # second pass
        for vertex in used_vertices:
            # convert to global space
            v = obj.matrix_world @ vertex.co

            # calculate distance to center to find out if the point is in or outside the sphere
            distance_center_to_v = distance_vec(mid_point, v)

            # point is outside the collision sphere
            if distance_center_to_v > radius:
                radius = (radius + distance_center_to_v) / 2
                old_to_new = distance_center_to_v - radius

                # calculate new_midpoint
                mid_point = (mid_point * radius + v * old_to_new) / distance_center_to_v

        return mid_point, radius

    def __init__(self):
        super().__init__()
        self.use_modifier_stack = True
        self.use_sphere_segments = True
        self.shape = "sphere_shape"

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
        if event.type == 'R' and event.value == 'RELEASE':
            self.set_modal_sphere_segments_active(context)
            
        # change bounding object settings
        if event.type == 'P' and event.value == 'RELEASE':
            self.my_use_modifier_stack = not self.my_use_modifier_stack
            self.execute(context)

        return {'RUNNING_MODAL'}


    def set_modal_sphere_segments_active(self, context):
        self.sphere_segments_active = not self.sphere_segments_active
        self.displace_active = False
        self.opacity_active = False
        self.decimate_active = False
        self.cylinder_segments_active = False
        self.execute(context)

    def execute(self, context):
        # CLEANUP
        super().execute(context)

        collider_data = []
        verts_co = []

        # Create the bounding geometry, depending on edit or object mode.
        for obj in self.selected_objects:

            # skip if invalid object
            if not self.is_valid_object(obj):
                continue

            initial_mod_state = {}
            context.view_layer.objects.active = obj
            scene = context.scene

            if self.obj_mode == "EDIT":
                used_vertices = self.get_vertices_Edit(obj, use_modifiers=self.my_use_modifier_stack)

            else:  # mode == "OBJECT":
                used_vertices = self.get_vertices_Object(obj, use_modifiers=self.my_use_modifier_stack)

            if used_vertices is None:  # Skip object if there is no Mesh data to create the collider
                continue

            bounding_sphere_data = {}

            if self.creation_mode[self.creation_mode_idx] == 'INDIVIDUAL':
                bounding_sphere_data['mid_point'], bounding_sphere_data['radius'] = self.calculate_bounding_sphere(obj,
                                                                                                                   used_vertices)
                bounding_sphere_data['parent'] = obj
                collider_data.append(bounding_sphere_data)

            else:  # if self.creation_mode[self.creation_mode_idx] == 'SELECTION':
                # get list of all vertex coordinates in global space
                ws_vtx_co = self.get_point_positions(obj, 'GLOBAL', used_vertices)
                verts_co = verts_co + ws_vtx_co

        if self.creation_mode[self.creation_mode_idx] == 'SELECTION':
            collider_data = self.bounding_sphere_data_selection(verts_co)
            
        for bounding_sphere_data in collider_data:
            mid_point = bounding_sphere_data['mid_point']
            radius = bounding_sphere_data['radius']
            parent = bounding_sphere_data['parent']

            new_collider = create_sphere(mid_point, radius, self.current_settings_dic['sphere_segments'])
            self.custom_set_parent(context, parent, new_collider)

            # save collision objects to delete when canceling the operation
            self.new_colliders_list.append(new_collider)
            collections = parent.users_collection
            self.primitive_postprocessing(context, new_collider, collections)

            super().set_collider_name(new_collider, parent.name)

        # Initial state has to be restored for the modal operator to work. If not, the result will break once changing the parameters
        super().reset_to_initial_state(context)
        elapsed_time = self.get_time_elapsed()
        super().print_generation_time("Sphere Collider", elapsed_time)
        self.report({'INFO'}, f"Sphere Collider: {float(elapsed_time)}")

        return {'RUNNING_MODAL'}

    def bounding_sphere_data_selection(self, verts_co):
        bounding_sphere_data = {}

        verts_co = self.transform_vertex_space(verts_co, self.active_obj)

        bm = bmesh.new()
        for v in verts_co:
            bm.verts.new(v)  # add a new vert
        me = bpy.data.meshes.new("mesh")
        bm.to_mesh(me)
        bm.free()

        bounding_sphere_data['mid_point'], bounding_sphere_data['radius'] = self.calculate_bounding_sphere(
            self.active_obj, me.vertices)
        bounding_sphere_data['parent'] = self.active_obj
        return [bounding_sphere_data]
