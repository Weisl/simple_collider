import random

import bmesh
import bpy
from bpy.types import Operator
from mathutils import Vector

from .add_bounding_primitive import OBJECT_OT_add_bounding_object

tmp_sphere_name = 'sphere_collider'


def _sphere_from_one(p):
    return p.copy(), 0.0


def _sphere_from_two(p1, p2):
    center = (p1 + p2) / 2
    radius = (p1 - p2).length / 2
    return center, radius


def _sphere_from_three(p1, p2, p3):
    a = p2 - p1
    b = p3 - p1
    cross = a.cross(b)
    denom = 2.0 * cross.length_squared
    if denom < 1e-12:
        # Degenerate: points are collinear, fall back to the pair with the largest distance
        d12 = (p1 - p2).length
        d13 = (p1 - p3).length
        d23 = (p2 - p3).length
        if d12 >= d13 and d12 >= d23:
            return _sphere_from_two(p1, p2)
        if d13 >= d23:
            return _sphere_from_two(p1, p3)
        return _sphere_from_two(p2, p3)
    t = (b.length_squared * cross.cross(a) + a.length_squared * b.cross(cross)) / denom
    center = p1 + t
    radius = t.length
    return center, radius


def _sphere_from_four(p1, p2, p3, p4):
    a = p2 - p1
    b = p3 - p1
    c = p4 - p1
    denom = 2.0 * a.dot(b.cross(c))
    if abs(denom) < 1e-12:
        # Degenerate: points are coplanar, try all triangles and pick the largest sphere
        candidates = [
            _sphere_from_three(p1, p2, p3),
            _sphere_from_three(p1, p2, p4),
            _sphere_from_three(p1, p3, p4),
            _sphere_from_three(p2, p3, p4),
        ]
        return max(candidates, key=lambda cr: cr[1])
    t = (c.length_squared * a.cross(b) + b.length_squared * c.cross(a) + a.length_squared * b.cross(c)) / denom
    center = p1 + t
    radius = t.length
    return center, radius


def _base_sphere(boundary):
    """Return (center, radius) for a sphere defined by up to 4 boundary points."""
    n = len(boundary)
    if n == 0:
        return Vector((0, 0, 0)), 0.0
    if n == 1:
        return _sphere_from_one(boundary[0])
    if n == 2:
        return _sphere_from_two(boundary[0], boundary[1])
    if n == 3:
        return _sphere_from_three(boundary[0], boundary[1], boundary[2])
    return _sphere_from_four(boundary[0], boundary[1], boundary[2], boundary[3])


def _welzl(points):
    """
    Compute the minimum enclosing sphere using Welzl's algorithm. Shuffles points in place.

    Uses an iterative formulation so that arbitrarily large point sets
    can be handled without hitting Python's recursion limit.

    See https://en.wikipedia.org/wiki/Smallest-circle_problem#Welzl's_algorithm
    """
    random.shuffle(points)
    n = len(points)
    stack = []  # (index, boundary) frames awaiting their "is p inside?" check
    idx = 0
    bnd = []  # points known to lie on the minimum enclosing sphere (up to 4)

    while True:
        # --- forward pass: advance to the base case ---
        if len(bnd) < 4:
            while idx < n:
                stack.append((idx, bnd))
                idx += 1

        # Reached base case — compute sphere from boundary points.
        center, radius = _base_sphere(bnd)

        # --- backward pass: unwind the stack, checking each point ---
        while stack:
            idx, bnd = stack.pop()
            p = points[idx]
            if (p - center).length > radius + 1e-7:
                # p is outside; restart forward pass from idx+1 with p on the boundary.
                bnd = bnd + [p]
                idx += 1
                break
        else:
            # Stack fully unwound — sphere encloses all points.
            return center, radius


def create_sphere(pos, diameter, segments):
    """Create a UV sphere at the given position with the specified diameter and segments."""
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

    for f in bm.faces:
        f.smooth = True

    bm.to_mesh(mesh)
    mesh.update()
    bm.clear()

    return basic_sphere


class OBJECT_OT_add_bounding_sphere(OBJECT_OT_add_bounding_object, Operator):
    """Create spherical colliders based on the selection"""
    bl_idname = "mesh.add_bounding_sphere"
    bl_label = "Add Sphere"
    bl_description = 'Create spherical colliders based on the selection'

    @staticmethod
    def calculate_bounding_sphere(obj, used_vertices):
        world_points = [obj.matrix_world @ vertex.co for vertex in used_vertices]
        return _welzl(world_points)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_modifier_stack = True
        self.use_sphere_segments = True
        self.shape = "sphere_shape"
        self.initial_shape = "sphere_shape"

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
            self.set_modal_state(sphere_segments_active=not self.sphere_segments_active)
            self.execute(context)

        # change bounding object settings
        if event.type == 'P' and event.value == 'RELEASE':
            self.my_use_modifier_stack = not self.my_use_modifier_stack
            self.execute(context)

        return {'RUNNING_MODAL'}

    def set_modal_state(self, cylinder_segments_active=False, displace_active=False, decimate_active=False,
                        opacity_active=False, sphere_segments_active=False, capsule_segments_active=False,
                        remesh_active=False, height_active=False, width_active=False):
        super().set_modal_state(cylinder_segments_active, displace_active, decimate_active,
                                opacity_active, sphere_segments_active, capsule_segments_active,
                                remesh_active, height_active, width_active)
        self.sphere_segments_active = sphere_segments_active

    def execute(self, context):
        # CLEANUP
        super().execute(context)

        collider_data = []
        verts_co = []

        objs = self.get_pre_processed_mesh_objs(context, default_world_spc=True)

        for base_ob, obj in objs:
            initial_mod_state = {}
            context.view_layer.objects.active = obj
            scene = context.scene

            if self.obj_mode == "EDIT" and base_ob.type == 'MESH' and self.active_obj.type == 'MESH' and not self.use_loose_mesh:
                used_vertices = self.get_edit_mode_vertices_local_space(obj, use_modifiers=self.my_use_modifier_stack)

            else:  # self.obj_mode  == "OBJECT" or self.use_loose_mesh == True:
                used_vertices = self.get_object_mode_vertices_local_space(obj, use_modifiers=self.my_use_modifier_stack)

            if used_vertices is None:  # Skip object if there is no Mesh data to create the collider
                continue

            bounding_sphere_data = {}

            creation_mode = self.creation_mode[self.creation_mode_idx] if self.obj_mode == 'OBJECT' else \
                self.creation_mode_edit[self.creation_mode_idx]

            if creation_mode in ['INDIVIDUAL'] or self.use_loose_mesh:

                bounding_sphere_data['mid_point'], bounding_sphere_data['radius'] = self.calculate_bounding_sphere(obj,
                                                                                                                   used_vertices)
                bounding_sphere_data['parent'] = base_ob
                collider_data.append(bounding_sphere_data)

            else:  # if self.creation_mode[self.creation_mode_idx] == 'SELECTION':
                # get list of all vertex coordinates in global space
                ws_vtx_co = self.get_vertex_coordinates(obj, 'GLOBAL', used_vertices)
                verts_co = verts_co + ws_vtx_co

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

        # Merge all collider objects
        if self.join_primitives:
            super().join_primitives(context)

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
