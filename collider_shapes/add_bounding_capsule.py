from math import radians

import bpy
import numpy as np
from bpy.types import Operator
from mathutils import Vector

from .add_bounding_primitive import OBJECT_OT_add_bounding_object
from .utilities import get_sca_matrix, get_rot_matrix, get_loc_matrix
from ..bmesh_operations.capsule_generation import create_capsule_data, mesh_data_to_bmesh
from ..bmesh_operations.cylinder_generation import welzl

tmp_name = 'capsule_collider'


def _welzl_center(nsphere):
    """Safely extract the 2-D centre from a Welzl minimum-enclosing-circle result.

    Different implementations expose the centre under different attribute names;
    we try the most common ones and fall back to the origin if none match.
    """
    for attr in ('center', 'centre', 'c'):
        val = getattr(nsphere, attr, None)
        if val is not None:
            return np.asarray(val, dtype=float).ravel()[:2]
    # Try explicit cx / cy attributes (some implementations use these)
    cx = getattr(nsphere, 'cx', None)
    cy = getattr(nsphere, 'cy', None)
    if cx is not None and cy is not None:
        return np.array([float(cx), float(cy)])
    return np.zeros(2)


def compute_minimal_capsule(t_coords, perp_coords):
    """Compute the tightest bounding capsule for a fixed axis direction.

    Theory
    ------
    For a capsule with radius *r* and hemispherical cap centres at axial
    positions *t_low* and *t_high*, a vertex at axial position *t_i* and
    perpendicular distance *d_i* from the axis is inside the capsule if and
    only if its distance to the axis *segment* is ≤ r.  Because we choose *r*
    from the minimum-enclosing circle in the perpendicular plane we already
    guarantee d_i ≤ r for every vertex, so:

    • Vertices with t_low ≤ t_i ≤ t_high are inside the cylinder – always OK.
    • Vertices below the cylinder (t_i < t_low) must be inside the bottom
      hemisphere:  (t_low − t_i)² + d_i² ≤ r²  →  t_low ≤ t_i + slack_i
    • Vertices above the cylinder (t_i > t_high) must be inside the top
      hemisphere:  (t_i − t_high)² + d_i² ≤ r²  →  t_high ≥ t_i − slack_i

    where  slack_i = √(r² − d_i²)  is how far the hemisphere can "reach"
    along the axis for vertex *i*.

    To minimise cylinder length we maximise t_low and minimise t_high:

        t_low  = min_i ( t_i + slack_i )
        t_high = max_i ( t_i − slack_i )

    When t_low > t_high the object fits inside a single sphere (no cylinder
    needed) and we collapse both cap centres to the midpoint.

    Parameters
    ----------
    t_coords   : sequence of float  – vertex positions along the capsule axis
    perp_coords: sequence of [x, y] – vertex positions in the perpendicular plane

    Returns
    -------
    radius     : float  – capsule radius
    depth      : float  – length of the cylindrical shaft (0 → pure sphere)
    t_center   : float  – capsule centre along the axis
    perp_center: [float, float] – axis centre in the perpendicular plane
    """
    perp_arr = np.asarray(perp_coords, dtype=float)
    t_arr    = np.asarray(t_coords,    dtype=float)

    # ── Step 1: minimum enclosing circle in the perpendicular plane ──────────
    nsphere     = welzl(perp_arr)
    radius      = float(np.sqrt(max(0.0, nsphere.sqr_radius)))
    perp_center = _welzl_center(nsphere)

    # ── Step 2: perpendicular distances from the optimal axis centre ─────────
    d_perp = np.linalg.norm(perp_arr - perp_center, axis=1)

    # ── Step 3: axial slack for each vertex ──────────────────────────────────
    # clamp to 0 to guard against floating-point noise when d_perp ≈ radius
    sqr_slacks = np.maximum(0.0, radius ** 2 - d_perp ** 2)
    slacks     = np.sqrt(sqr_slacks)

    # ── Step 4: tightest cap positions ───────────────────────────────────────
    t_low  = float(np.min(t_arr + slacks))   # bottom hemisphere centre
    t_high = float(np.max(t_arr - slacks))   # top    hemisphere centre

    if t_low > t_high:
        # All vertices fit inside a single sphere – collapse to a sphere
        t_mid  = (t_low + t_high) * 0.5
        t_low  = t_mid
        t_high = t_mid

    depth    = max(0.0, t_high - t_low)
    t_center = (t_low + t_high) * 0.5

    return radius, depth, t_center, perp_center.tolist()


def _build_world_center_local_space(t_center, perp_center, axis, loc, rot):
    """Convert an optimal capsule centre from 'scaled-local' space to world space.

    In LOCAL mode the vertex coordinates are pre-multiplied by the object's
    scale matrix, so a point in that space maps to world space via:

        p_world = loc + rot_matrix @ p_scaled_local

    Parameters
    ----------
    t_center   : float           – capsule centre along the capsule axis (scaled-local)
    perp_center: [float, float]  – capsule centre in the perpendicular plane (scaled-local)
    axis       : str             – 'X', 'Y', or 'Z'
    loc        : mathutils.Vector
    rot        : mathutils.Quaternion
    """
    pc = perp_center
    if axis == 'X':
        # perp plane is YZ;  coordinates order was [v.y, v.z]
        scaled_local = Vector((t_center, pc[0], pc[1]))
    elif axis == 'Y':
        # perp plane is XZ;  coordinates order was [v.x, v.z]
        scaled_local = Vector((pc[0], t_center, pc[1]))
    else:  # 'Z'
        # perp plane is XY;  coordinates order was [v.x, v.y]
        scaled_local = Vector((pc[0], pc[1], t_center))

    return Vector(loc) + rot.to_matrix() @ scaled_local


def _build_world_center_global_space(t_center, perp_center, axis):
    """Construct the world-space capsule centre from global-space capsule parameters."""
    pc = perp_center
    if axis == 'X':
        return [t_center, pc[0], pc[1]]
    elif axis == 'Y':
        return [pc[0], t_center, pc[1]]
    else:  # 'Z'
        return [pc[0], pc[1], t_center]


class OBJECT_OT_add_bounding_capsule(OBJECT_OT_add_bounding_object, Operator):
    """Create bounding capsule collider based on the selection"""
    bl_idname = "mesh.add_bounding_capsule"
    bl_label = "Add Capsule (Beta)"
    bl_description = 'Create bounding capsule colliders based on the selection'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shape = 'capsule_shape'
        self.initial_shape = 'capsule_shape'

        self.use_space = True
        self.use_modifier_stack = True
        self.use_global_local_switches = True

        # Capsule specific
        self.use_capsule_axis = True
        self.use_capsule_segments = True
        self.use_height_multiplier = True
        self.use_width_multiplier = True

    def get_used_vertices(self, base_ob, obj):
        if self.obj_mode == "EDIT" and base_ob.type == 'MESH' and self.active_obj.type == 'MESH' and not self.use_loose_mesh:
            return self.get_edit_mode_vertices_local_space(obj, use_modifiers=self.my_use_modifier_stack)
        else:
            return self.get_object_mode_vertices_local_space(obj, use_modifiers=self.my_use_modifier_stack)

    def set_modal_state(self, cylinder_segments_active=False, displace_active=False, decimate_active=False,
                        opacity_active=False, sphere_segments_active=False, capsule_segments_active=False,
                        remesh_active=False, height_active=False, width_active=False):
        super().set_modal_state(cylinder_segments_active, displace_active, decimate_active, opacity_active,
                                sphere_segments_active, capsule_segments_active, remesh_active, height_active,
                                width_active)
        self.capsule_segments_active = capsule_segments_active

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

        if event.type == 'G' and event.value == 'RELEASE':
            self.my_space = 'GLOBAL'
            self.execute(context)

        elif event.type == 'L' and event.value == 'RELEASE':
            self.my_space = 'LOCAL'
            self.execute(context)

        if event.type == 'R' and event.value == 'RELEASE':
            self.set_modal_state(capsule_segments_active=not self.capsule_segments_active)
            self.execute(context)

        if event.type == 'P' and event.value == 'RELEASE':
            self.my_use_modifier_stack = not self.my_use_modifier_stack
            self.execute(context)

        elif event.type in {'X', 'Y', 'Z'} and event.value == 'RELEASE':
            self.cylinder_axis = event.type
            self.execute(context)

        return {'RUNNING_MODAL'}

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _split_axis(v, axis):
        """Return (perp_2d, t) for a vertex vector, split by the capsule axis."""
        if axis == 'X':
            return [v.y, v.z], v.x
        elif axis == 'Y':
            return [v.x, v.z], v.y
        else:  # 'Z'
            return [v.x, v.y], v.z

    # ── execute ───────────────────────────────────────────────────────────────

    def execute(self, context):
        super().execute(context)

        collider_data = []
        verts_co      = []

        objs = self.get_pre_processed_mesh_objs(context)

        for base_ob, obj in objs:
            used_vertices = self.get_used_vertices(base_ob, obj)
            if not used_vertices:
                continue

            matrix_WS      = obj.matrix_world
            loc, rot, sca  = matrix_WS.decompose()

            creation_mode = (
                self.creation_mode[self.creation_mode_idx]
                if self.obj_mode == 'OBJECT'
                else self.creation_mode_edit[self.creation_mode_idx]
            )

            # ── INDIVIDUAL / loose-mesh mode ──────────────────────────────────
            if creation_mode in ['INDIVIDUAL'] or self.use_loose_mesh:

                perp_coords = []
                t_coords    = []

                for vertex in used_vertices:
                    if self.my_space == 'LOCAL':
                        # Scale only – rotation/translation handled when
                        # converting the centre back to world space.
                        v = vertex.co @ get_sca_matrix(sca)
                    else:
                        v = vertex.co @ get_sca_matrix(sca) @ get_loc_matrix(loc) @ get_rot_matrix(rot)

                    perp, t = self._split_axis(v, self.cylinder_axis)
                    perp_coords.append(perp)
                    t_coords.append(t)

                radius, depth, t_center, perp_center = compute_minimal_capsule(
                    t_coords, perp_coords
                )

                # Build the 3-D capsule centre
                if self.my_space == 'LOCAL':
                    center = _build_world_center_local_space(
                        t_center, perp_center, self.cylinder_axis, loc, rot
                    )
                else:
                    center = _build_world_center_global_space(
                        t_center, perp_center, self.cylinder_axis
                    )

                collider_data.append({
                    'parent':       base_ob,
                    'radius':       radius,
                    'depth':        depth,
                    'center_point': list(center),
                })

            # ── SELECTION mode ────────────────────────────────────────────────
            else:
                if self.shape == 'LOCAL':
                    ws_vtx_co = self.get_vertex_coordinates(obj, 'GLOBAL', used_vertices)
                    verts_co  = verts_co + self.transform_vertex_space(ws_vtx_co, self.active_obj)
                else:
                    ws_vtx_co = self.get_vertex_coordinates(obj, 'GLOBAL', used_vertices)
                    verts_co  = verts_co + ws_vtx_co

                perp_coords = []
                t_coords    = []

                for v in verts_co:
                    perp, t = self._split_axis(v, self.cylinder_axis)
                    perp_coords.append(perp)
                    t_coords.append(t)

                radius, depth, t_center, perp_center = compute_minimal_capsule(
                    t_coords, perp_coords
                )

                center = _build_world_center_global_space(
                    t_center, perp_center, self.cylinder_axis
                )

                collider_data = [{
                    'parent':       self.active_obj,
                    'radius':       radius,
                    'depth':        depth,
                    'center_point': list(center),
                }]

        # ── create collider meshes ────────────────────────────────────────────
        bpy.context.view_layer.objects.active = self.active_obj
        bpy.ops.object.mode_set(mode='OBJECT')

        settings = self.current_settings_dic

        for bounding_capsule_data in collider_data:
            parent = bounding_capsule_data['parent']
            radius = bounding_capsule_data['radius']
            depth  = bounding_capsule_data['depth']
            center = bounding_capsule_data['center_point']

            capsule_data = create_capsule_data(
                longitudes  = settings['capsule_segments'],
                latitudes   = int(settings['capsule_segments']),
                radius      = radius * settings['width_mult'],
                depth       = depth  * settings['height_mult'],
                uv_profile  = "FIXED",
            )

            bm = mesh_data_to_bmesh(
                vs        = capsule_data["vs"],
                vts       = capsule_data["vts"],
                vns       = capsule_data["vns"],
                v_indices = capsule_data["v_indices"],
                vt_indices= capsule_data["vt_indices"],
                vn_indices= capsule_data["vn_indices"],
            )

            mesh_data = bpy.data.meshes.new("Capsule")
            bm.to_mesh(mesh_data)
            bm.free()

            new_collider          = bpy.data.objects.new(mesh_data.name, mesh_data)
            new_collider.location = center

            rotation_euler = parent.rotation_euler
            if rotation_euler:
                new_collider.rotation_euler = rotation_euler

            # Align capsule to the chosen axis (create_capsule_data aligns along Z by default)
            if self.cylinder_axis == 'X':
                new_collider.rotation_euler.rotate_axis("Y", radians(90))
            elif self.cylinder_axis == 'Y':
                new_collider.rotation_euler.rotate_axis("X", radians(90))

            self.new_colliders_list.append(new_collider)
            collections = parent.users_collection
            self.primitive_postprocessing(context, new_collider, collections)

            super().set_collider_name(new_collider, parent.name)
            self.custom_set_parent(context, parent, new_collider)

        if self.join_primitives:
            super().join_primitives(context)

        super().reset_to_initial_state(context)
        elapsed_time = self.get_time_elapsed()
        super().print_generation_time("Capsule Collider", elapsed_time)
        self.report({'INFO'}, f"Capsule Collider: {float(elapsed_time)}")

        return {'RUNNING_MODAL'}