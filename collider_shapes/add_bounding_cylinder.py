import bpy
import numpy as np

from math import sqrt, radians

from bpy.types import Operator
from mathutils import Matrix, Vector
from .utilities import get_sca_matrix, get_rot_matrix, get_loc_matrix
from .add_bounding_primitive import OBJECT_OT_add_bounding_object

tmp_name = 'cylindrical_collider'

class ProjectorStack:
    """
    Stack of points that are shifted / projected to put first one at origin.
    """

    def __init__(self, vec):
        self.vs = np.array(vec)

    def push(self, v):
        if len(self.vs) == 0:
            self.vs = np.array([v])
        else:
            self.vs = np.append(self.vs, [v], axis=0)
        return self

    def pop(self):
        if len(self.vs) > 0:
            ret, self.vs = self.vs[-1], self.vs[:-1]
            return ret

    def __mul__(self, v):
        s = np.zeros(len(v))
        for vi in self.vs:
            s = s + vi * np.dot(vi, v)
        return s


class GaertnerBoundary:
    """
        GärtnerBoundary

    See the passage regarding M_B in Section 4 of Gärtner's paper.
    """

    def __init__(self, pts):
        self.projector = ProjectorStack([])
        self.centers, self.square_radii = np.array([]), np.array([])
        self.empty_center = np.array([np.NaN for _ in pts[0]])


def push_if_stable(bound, pt):
    if len(bound.centers) == 0:
        bound.square_radii = np.append(bound.square_radii, 0.0)
        bound.centers = np.array([pt])
        return True
    q0, center = bound.centers[0], bound.centers[-1]
    C, r2 = center - q0, bound.square_radii[-1]
    Qm, M = pt - q0, bound.projector
    Qm_bar = M * Qm
    residue, e = Qm - Qm_bar, sqdist(Qm, C) - r2
    z, tol = 2 * sqnorm(residue), np.finfo(float).eps * max(r2, 1.0)
    isstable = np.abs(z) > tol
    if isstable:
        center_new = center + (e / z) * residue
        r2new = r2 + (e * e) / (2 * z)
        bound.projector.push(residue / np.linalg.norm(residue))
        bound.centers = np.append(
            bound.centers, np.array([center_new]), axis=0)
        bound.square_radii = np.append(bound.square_radii, r2new)
    return isstable


def pop(bound):
    n = len(bound.centers)
    bound.centers = bound.centers[:-1]
    bound.square_radii = bound.square_radii[:-1]
    if n >= 2:
        bound.projector.pop()
    return bound


class NSphere:
    def __init__(self, c, sqr):
        self.center = np.array(c)
        self.sqradius = sqr


def isinside(pt, nsphere, atol=1e-6, rtol=0.0):
    r2, R2 = sqdist(pt, nsphere.center), nsphere.sqradius
    return r2 <= R2 or np.isclose(r2, R2, atol=atol**2, rtol=rtol**2)


def allinside(pts, nsphere, atol=1e-6, rtol=0.0):
    return all(isinside(p, nsphere, atol, rtol) for p in pts)


def move_to_front(pts, i):
    pt = pts[i]
    for j in range(len(pts)):
        pts[j], pt = pt, np.array(pts[j])
        if j == i:
            break
    return pts


def dist(p1, p2):
    return np.linalg.norm(p1 - p2)


def sqdist(p1, p2):
    return sqnorm(p1 - p2)


def sqnorm(p):
    return np.sum(np.array([x * x for x in p]))


def ismaxlength(bound):
    len(bound.centers) == len(bound.empty_center) + 1


def makeNSphere(bound):
    if len(bound.centers) == 0:
        return NSphere(bound.empty_center, 0.0)
    return NSphere(bound.centers[-1], bound.square_radii[-1])


def _welzl(pts, pos, bdry):
    support_count, nsphere = 0, makeNSphere(bdry)
    if ismaxlength(bdry):
        return nsphere, 0
    for i in range(pos):
        if not isinside(pts[i], nsphere):
            isstable = push_if_stable(bdry, pts[i])
            if isstable:
                nsphere, s = _welzl(pts, i, bdry)
                pop(bdry)
                move_to_front(pts, i)
                support_count = s + 1
    return nsphere, support_count


def find_max_excess(nsphere, pts, k1):
    err_max, k_max = -np.Inf, k1 - 1
    for (k, pt) in enumerate(pts[k_max:]):
        err = sqdist(pt, nsphere.center) - nsphere.sqradius
        if err > err_max:
            err_max, k_max = err, k + k1
    return err_max, k_max - 1


def welzl(points, maxiterations=2000):
    pts, eps = np.array(points, copy=True), np.finfo(float).eps
    bdry, t = GaertnerBoundary(pts), 1
    nsphere, s = _welzl(pts, t, bdry)
    for i in range(maxiterations):
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
        self.shape = 'convex_shape'

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
        colSettings = context.scene.collider_tools

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
        # CLEANUP
        super().execute(context)
        colSettings = context.scene.collider_tools

        collider_data = []
        verts_co = []

        for obj in context.selected_objects.copy():

            # skip if invalid object
            if not self.is_valid_object(obj):
                continue

            bounding_cylinder_data = {}

            if self.obj_mode == 'EDIT':
                used_vertices = self.get_vertices_Edit(
                    obj, use_modifiers=self.my_use_modifier_stack)
            else:
                used_vertices = self.get_vertices_Object(
                    obj, use_modifiers=self.my_use_modifier_stack)

            if not used_vertices:
                continue

            matrix_WS = obj.matrix_world
            loc, rot, sca = matrix_WS.decompose()

            if self.creation_mode[self.creation_mode_idx] == 'INDIVIDUAL':

                coordinates = []
                height = []

                co = self.get_point_positions(
                    obj, self.my_space, used_vertices)
                bounding_box, center = self.generate_bounding_box(co)

                for vertex in used_vertices:

                    # Ignore Scale
                    if self.my_space == 'LOCAL':
                        v = vertex.co @ get_sca_matrix(sca)
                        center = sum((Vector(matrix_WS @ Vector(b))
                                     for b in bounding_box), Vector()) / 8.0
                    else:
                        # Scale has to be applied before location
                        v = vertex.co @ get_sca_matrix(
                            sca) @ get_loc_matrix(loc) @ get_rot_matrix(rot)
                        center = sum((Vector(b)
                                     for b in bounding_box), Vector()) / 8.0

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
                radius = np.sqrt(nsphere.sqradius)

                bounding_cylinder_data['parent'] = obj
                bounding_cylinder_data['radius'] = radius
                bounding_cylinder_data['depth'] = depth
                bounding_cylinder_data['center_point'] = [
                    center[0], center[1], center[2]]
                collider_data.append(bounding_cylinder_data)

            else:  # if self.creation_mode[self.creation_mode_idx] == 'SELECTION':
                # get list of all vertex coordinates in global space
                ws_vtx_co = self.get_point_positions(obj, 'GLOBAL', used_vertices)
                verts_co = verts_co + ws_vtx_co
 

        if self.creation_mode[self.creation_mode_idx] == 'SELECTION':
            bounding_box, center = self.generate_bounding_box(verts_co)        
            
            if self.prefs.debug:
                debug_obj = self.create_debug_object_from_verts(context, verts_co)
            
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
            radius = np.sqrt(nsphere.sqradius)

            bounding_cylinder_data['parent'] = self.active_obj
            bounding_cylinder_data['radius'] = radius
            bounding_cylinder_data['depth'] = depth
            bounding_cylinder_data['center_point'] = [
                    center[0], center[1], center[2]]
            collider_data = [bounding_cylinder_data]

        bpy.ops.object.mode_set(mode='OBJECT')

        for bounding_cylinder_data in collider_data:
            global tmp_name

            parent = bounding_cylinder_data['parent']
            radius = bounding_cylinder_data['radius']
            depth = bounding_cylinder_data['depth']
            center = bounding_cylinder_data['center_point']

            if  self.my_space == 'GLOBAL' or self.creation_mode[self.creation_mode_idx] == 'SELECTION':
                new_collider = self.generate_cylinder_object(
                    context, radius, depth, center)
                
            else: # if self.my_space == 'LOCAL':
                new_collider = self.generate_cylinder_object(context, radius, depth, center,
                                                             rotation_euler=parent.rotation_euler)
                new_collider.scale = (1.0, 1.0, 1.0)

            self.new_colliders_list.append(new_collider)
            collections = parent.users_collection
            self.primitive_postprocessing(context, new_collider, collections)

            super().set_collider_name(new_collider, parent.name)
            self.custom_set_parent(context, parent, new_collider)

        super().reset_to_initial_state(context)
        elapsed_time = self.get_time_elapsed()
        super().print_generation_time("Convex Cylindrical Collider", elapsed_time)
        self.report(
            {'INFO'}, f"Convex Cylindrical Collider: {float(elapsed_time)}")

        return {'RUNNING_MODAL'}
