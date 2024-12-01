from math import radians

import bpy
import numpy as np
from bpy.types import Operator
from mathutils import Vector

from .add_bounding_primitive import OBJECT_OT_add_bounding_object
from .utilities import get_sca_matrix, get_rot_matrix, get_loc_matrix

tmp_name = 'cylindrical_collider'


class ProjectorStack:
    """
    Stack of points that are shifted / projected to put the first one at origin.

    Attributes:
        vs (np.array): Array of vectors.
    """

    def __init__(self, vec):
        """
        Initialize the ProjectorStack with a list of vectors.

        Args:
            vec (list): List of vectors.
        """
        self.vs = np.array(vec)

    def push(self, v):
        """
        Add a new vector to the stack.

        Args:
            v (np.array): Vector to add.

        Returns:
            ProjectorStack: Updated stack.
        """
        if len(self.vs) == 0:
            self.vs = np.array([v])
        else:
            self.vs = np.append(self.vs, [v], axis=0)
        return self

    def pop(self):
        """
        Remove the last vector from the stack.

        Returns:
            np.array: The removed vector.
        """
        if len(self.vs) > 0:
            ret, self.vs = self.vs[-1], self.vs[:-1]
            return ret

    def __mul__(self, v):
        """
        Multiply the stack of vectors by a given vector.

        Args:
            v (np.array): Vector to multiply with.

        Returns:
            np.array: Resulting vector after multiplication.
        """
        s = np.zeros(len(v))
        for vi in self.vs:
            s = s + vi * np.dot(vi, v)
        return s


class GaertnerBoundary:
    """
    GärtnerBoundary

    Manages the boundary conditions based on Gärtner's paper.

    Attributes:
        projector (ProjectorStack): Projector stack for managing points.
        centers (np.array): Array of center points.
        square_radii (np.array): Array of squared radii.
        empty_center (np.array): Empty center array.
    """

    def __init__(self, pts):
        """
        Initialize the GärtnerBoundary with a list of points.

        Args:
            pts (list): List of points.
        """
        self.projector = ProjectorStack([])
        self.centers, self.square_radii = np.array([]), np.array([])
        self.empty_center = np.array([np.NaN for _ in pts[0]])


def push_if_stable(bound, pt):
    """
    Attempts to push a point into the boundary if stable.

    Args:
        bound (GaertnerBoundary): The boundary to push into.
        pt (np.array): The point to push.

    Returns:
        bool: True if the point was successfully pushed, False otherwise.
    """

    if len(bound.centers) == 0:
        bound.square_radii = np.append(bound.square_radii, 0.0)
        bound.centers = np.array([pt])
        return True
    q0, center = bound.centers[0], bound.centers[-1]
    C, r2 = center - q0, bound.square_radii[-1]
    Qm, M = pt - q0, bound.projector
    Qm_bar = M * Qm
    residue, e = Qm - Qm_bar, sqr_dist(Qm, C) - r2
    z, tol = 2 * sqr_norm(residue), np.finfo(float).eps * max(r2, 1.0)
    is_stable = np.abs(z) > tol
    if is_stable:
        center_new = center + (e / z) * residue
        r2new = r2 + (e * e) / (2 * z)
        bound.projector.push(residue / np.linalg.norm(residue))
        bound.centers = np.append(
            bound.centers, np.array([center_new]), axis=0)
        bound.square_radii = np.append(bound.square_radii, r2new)
    return is_stable


def pop(bound):
    """
    Removes the last point from the boundary.

    Args:
        bound (GaertnerBoundary): The boundary to remove the point from.

    Returns:
        GaertnerBoundary: Updated boundary.
    """
    n = len(bound.centers)
    bound.centers = bound.centers[:-1]
    bound.square_radii = bound.square_radii[:-1]
    if n >= 2:
        bound.projector.pop()
    return bound


class NSphere:
    """
    Represents a hypersphere with a center and squared radius.

    Attributes:
        center (np.array): Center of the n-sphere.
        sqr_radius (float): Squared radius of the n-sphere.
    """

    def __init__(self, c, sqr):
        """
        Initialize the NSphere with a center and squared radius.

        Args:
            c (np.array): Center of the n-sphere.
            sqr (float): Squared radius of the n-sphere.
        """
        self.center = np.array(c)
        self.sqr_radius = sqr


def is_inside(pt, nsphere, atol=1e-6, rtol=0.0):
    """
    Checks if a point is inside the n-sphere.

    Args:
        pt (np.array): The point to check.
        nsphere (NSphere): The n-sphere to check against.
        atol (float): Absolute tolerance for closeness check.
        rtol (float): Relative tolerance for closeness check.

    Returns:
        bool: True if the point is inside the n-sphere, False otherwise.
    """
    r2, R2 = sqr_dist(pt, nsphere.center), nsphere.sqr_radius
    return r2 <= R2 or np.isclose(r2, R2, atol=atol ** 2, rtol=rtol ** 2)


def all_inside(pts, nsphere, atol=1e-6, rtol=0.0):
    """
    Checks if all points are inside the n-sphere.

    Args:
        pts (list): List of points to check.
        nsphere (NSphere): The n-sphere to check against.
        atol (float): Absolute tolerance for closeness check.
        rtol (float): Relative tolerance for closeness check.

    Returns:
        bool: True if all points are inside the n-sphere, False otherwise.
    """
    return all(is_inside(p, nsphere, atol, rtol) for p in pts)


def move_to_front(pts, i):
    """
    Moves a point to the front of the list.

    Args:
        pts (list): List of points.
        i (int): Index of the point to move.

    Returns:
        list: Updated list of points.
    """
    pt = pts[i]
    for j in range(len(pts)):
        pts[j], pt = pt, np.array(pts[j])
        if j == i:
            break
    return pts


def dist(p1, p2):
    """
    Calculates the Euclidean distance between two points.

    Args:
        p1 (np.array): First point.
        p2 (np.array): Second point.

    Returns:
        float: Euclidean distance between the points.
    """
    return np.linalg.norm(p1 - p2)


def sqr_dist(p1, p2):
    """
    Calculates the squared distance between two points.

    Args:
        p1 (np.array): First point.
        p2 (np.array): Second point.

    Returns:
        float: Squared distance between the points.
    """
    return sqr_norm(p1 - p2)


def sqr_norm(p):
    """
    Calculates the squared norm of a point.

    Args:
        p (np.array): Point to calculate the squared norm for.

    Returns:
        float: Squared norm of the point.
    """
    return np.sum(np.array([x * x for x in p]))


def is_max_length(bound):
    """
    Checks if the boundary has reached its maximum length.

    Args:
        bound (GaertnerBoundary): The boundary to check.

    Returns:
        bool: True if the boundary is at maximum length, False otherwise.
    """
    len(bound.centers) == len(bound.empty_center) + 1


def makeNSphere(bound):
    """
    Creates an n-sphere from the boundary.

    Args:
        bound (GaertnerBoundary): The boundary to create the n-sphere from.

    Returns:
        NSphere: The created n-sphere.
    """
    if len(bound.centers) == 0:
        return NSphere(bound.empty_center, 0.0)
    return NSphere(bound.centers[-1], bound.square_radii[-1])


def _welzl(pts, pos, bdry):
    """
    Recursive helper function for Welzl's algorithm.

    Args:
        pts (list): List of points.
        pos (int): Current position in the list of points.
        bdry (GaertnerBoundary): Current boundary.

    Returns:
        tuple: The resulting n-sphere and support count.
    """
    support_count, nsphere = 0, makeNSphere(bdry)
    if is_max_length(bdry):
        return nsphere, 0
    for i in range(pos):
        if not is_inside(pts[i], nsphere):
            is_stable = push_if_stable(bdry, pts[i])
            if is_stable:
                nsphere, s = _welzl(pts, i, bdry)
                pop(bdry)
                move_to_front(pts, i)
                support_count = s + 1
    return nsphere, support_count


def find_max_excess(nsphere, pts, k1):
    """
    Finds the point with the maximum excess error.

    Args:
        nsphere (NSphere): The current n-sphere.
        pts (list): List of points.
        k1 (int): Starting index for the search.

    Returns:
        tuple: The maximum error and index of the point with maximum error.
    """
    err_max, k_max = -np.Inf, k1 - 1
    for (k, pt) in enumerate(pts[k_max:]):
        err = sqr_dist(pt, nsphere.center) - nsphere.sqr_radius
        if err > err_max:
            err_max, k_max = err, k + k1
    return err_max, k_max - 1


def welzl(points, max_iterations=2000):
    """
    Finds the smallest enclosing n-sphere for a set of points.

    Args:
        points (list): List of points.
        max_iterations (int): Maximum number of iterations.

    Returns:
        NSphere: The resulting smallest enclosing n-sphere.
    """
    pts, eps = np.array(points, copy=True), np.finfo(float).eps
    bdry, t = GaertnerBoundary(pts), 1
    nsphere, s = _welzl(pts, t, bdry)
    for i in range(max_iterations):
        e, k = find_max_excess(nsphere, pts, t + 1)
        if e <= eps:
            break
        pt = pts[k]
        push_if_stable(bdry, pt)
        nsphere_new, s_new = _welzl(pts, s, bdry)
        pop(bdry)
        move_to_front(pts, k)
        nsphere = nsphere_new
        t, s = s + 1, s_new + 1
    return nsphere


class OBJECT_OT_add_bounding_cylinder(OBJECT_OT_add_bounding_object, Operator):
    """Create cylindrical bounding collisions based on the selection"""
    bl_idname = "mesh.add_bounding_cylinder"
    bl_label = "Add Cylinder"
    bl_description = 'Create cylindrical colliders based on the selection'

    def generate_cylinder_object(self, context, radius, depth, location, rotation_euler=False):
        """
        Create cylindrical collider for every selected object in object mode.

        Args:
            context: Blender context.
            radius (float): Radius of the cylinder.
            depth (float): Depth of the cylinder.
            location (tuple): Location of the cylinder.
            rotation_euler (tuple, optional): Rotation of the cylinder.

        Returns:
            bpy.types.Object: The created cylindrical collider.
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

    def get_used_vertices(self, base_ob, obj):
        if self.obj_mode == "EDIT" and base_ob.type == 'MESH' and self.active_obj.type == 'MESH' and not self.use_loose_mesh:
            return self.get_edit_mode_vertices_local_space(obj, use_modifiers=self.my_use_modifier_stack)
        else:
            return self.get_object_mode_vertices_local_space(obj, use_modifiers=self.my_use_modifier_stack)

    def __init__(self):
        """
        Initialize the OBJECT_OT_add_bounding_cylinder operator.
        """
        super().__init__()
        self.use_space = True
        self.use_modifier_stack = True
        self.use_global_local_switches = True

        # cylinder specific
        self.use_cylinder_segments = True
        self.use_cylinder_axis = True
        self.shape = 'convex_shape'
        self.initial_shape = 'convex_shape'

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

        # change bounding object settings
        if event.type == 'G' and event.value == 'RELEASE':
            self.my_space = 'GLOBAL'
            self.execute(context)

        elif event.type == 'L' and event.value == 'RELEASE':
            self.my_space = 'LOCAL'
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
        # Call the parent class's execute method for any necessary initialization or cleanup
        super().execute(context)

        # Initialize lists to store collider data and vertex coordinates
        collider_data = []
        verts_co = []

        # Get the pre-processed mesh objects from the context
        objs = self.get_pre_processed_mesh_objs(context)

        # Iterate through each base object and its corresponding processed object
        for base_ob, obj in objs:
            # Initialize a dictionary to store data for the bounding cylinder
            bounding_cylinder_data = {}

            # Get the vertices that will be used for processing based on the mode and object type
            used_vertices = self.get_used_vertices(base_ob, obj)

            # If no vertices are found, skip to the next object
            if not used_vertices:
                continue


            # Decompose the object's world matrix into location, rotation, and scale components
            matrix_WS = obj.matrix_world
            loc, rot, sca = matrix_WS.decompose()

            creation_mode = self.creation_mode[self.creation_mode_idx] if self.obj_mode == 'OBJECT' else \
                self.creation_mode_edit[self.creation_mode_idx]

            if creation_mode in ['INDIVIDUAL'] or self.use_loose_mesh:
                coordinates = []
                height = []

                co = self.get_vertex_coordinates(
                    obj, self.my_space, used_vertices)
                bounding_box, center = self.generate_bounding_box(co)

                for vertex in used_vertices:

                    # Ignore Scale
                    if self.my_space == 'LOCAL':
                        v = vertex.co @ get_sca_matrix(sca)
                    else:
                        # Scale has to be applied before location
                        v = vertex.co @ get_sca_matrix(
                            sca) @ get_loc_matrix(loc) @ get_rot_matrix(rot)

                    if self.cylinder_axis == 'X':
                        coordinates.append([v.y, v.z])
                        height.append(v.x)
                    elif self.cylinder_axis == 'Y':
                        coordinates.append([v.x, v.z])
                        height.append(v.y)
                    elif self.cylinder_axis == 'Z':
                        coordinates.append([v.x, v.y])
                        height.append(v.z)


                if self.my_space == 'LOCAL':
                    center = sum((Vector(matrix_WS @ Vector(b))
                                  for b in bounding_box), Vector()) / 8.0
                else:
                    center = sum((Vector(b)
                                  for b in bounding_box), Vector()) / 8.0

                depth = abs(max(height) - min(height))
                nsphere = welzl(np.array(coordinates))
                radius = np.sqrt(nsphere.sqr_radius)

                bounding_cylinder_data['parent'] = base_ob
                bounding_cylinder_data['radius'] = radius
                bounding_cylinder_data['depth'] = depth
                bounding_cylinder_data['center_point'] = [
                    center[0], center[1], center[2]]
                collider_data.append(bounding_cylinder_data)

            else:  # if self.creation_mode[self.creation_mode_idx] == 'SELECTION':

                if self.shape == 'LOCAL':
                    ws_vtx_co = self.get_vertex_coordinates(obj, 'GLOBAL', used_vertices)
                    verts_co = verts_co + self.transform_vertex_space(ws_vtx_co, self.active_obj)
                else:
                    ws_vtx_co = self.get_vertex_coordinates(obj, 'GLOBAL', used_vertices)
                verts_co = verts_co + ws_vtx_co

                coordinates = []
                height = []

                # Scale has to be applied before location
                # v = vertex.co @ get_sca_matrix(sca) @ get_loc_matrix(loc) @ get_rot_matrix(rot)
                bounding_box, center = self.generate_bounding_box(verts_co)
                center = sum((Vector(b) for b in bounding_box), Vector()) / 8.0

                for v in verts_co:
                    if self.cylinder_axis == 'X':
                        coordinates.append([v.y, v.z])
                        height.append(v.x)
                    elif self.cylinder_axis == 'Y':
                        coordinates.append([v.x, v.z])
                        height.append(v.y)
                    elif self.cylinder_axis == 'Z':
                        coordinates.append([v.x, v.y])
                        height.append(v.z)

                depth = abs(max(height) - min(height))

                nsphere = welzl(np.array(coordinates))
                radius = np.sqrt(nsphere.sqr_radius)

                bounding_cylinder_data['parent'] = self.active_obj
                bounding_cylinder_data['radius'] = radius
                bounding_cylinder_data['depth'] = depth
                bounding_cylinder_data['center_point'] = [
                        center[0], center[1], center[2]]
                collider_data = [bounding_cylinder_data]


        bpy.context.view_layer.objects.active = self.active_obj
        bpy.ops.object.mode_set(mode='OBJECT')

        for bounding_cylinder_data in collider_data:
            global tmp_name

            parent = bounding_cylinder_data['parent']
            radius = bounding_cylinder_data['radius']
            depth = bounding_cylinder_data['depth']
            center = bounding_cylinder_data['center_point']

            if self.my_space == 'GLOBAL':
                new_collider = self.generate_cylinder_object(
                    context, radius, depth, center)

            else:  # if self.my_space == 'LOCAL':
                new_collider = self.generate_cylinder_object(context, radius, depth, center,
                                                             rotation_euler=parent.rotation_euler)
                new_collider.scale = (1.0, 1.0, 1.0)

            self.new_colliders_list.append(new_collider)
            collections = parent.users_collection
            self.primitive_postprocessing(context, new_collider, collections)

            super().set_collider_name(new_collider, parent.name)
            self.custom_set_parent(context, parent, new_collider)

        # Merge all collider objects
        if self.join_primitives:
            super().join_primitives(context)

        super().reset_to_initial_state(context)
        elapsed_time = self.get_time_elapsed()
        super().print_generation_time("Convex Cylindrical Collider", elapsed_time)
        self.report(
            {'INFO'}, f"Convex Cylindrical Collider: {float(elapsed_time)}")

        return {'RUNNING_MODAL'}
