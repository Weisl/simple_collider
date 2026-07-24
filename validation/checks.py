import re
from dataclasses import dataclass

import bmesh
import numpy as np

from ..bmesh_operations.voxel_generation import mesh_max_dimension
from ..collider_shapes.add_bounding_sphere import OBJECT_OT_add_bounding_sphere
from ..collider_shapes.add_minimum_bounding_box import OBJECT_OT_add_aligned_bounding_box
from ..properties.constants import VALID_OBJECT_TYPES


@dataclass(frozen=True)
class ValidationIssue:
    check_id: str
    object_name: str
    severity: str  # 'ERROR' or 'WARNING'
    message: str


def _world_coords(obj, depsgraph):
    """World-space vertex coordinates of obj's evaluated mesh, as an (N, 3) array."""
    obj_eval = obj.evaluated_get(depsgraph)
    mesh = obj_eval.data
    if len(mesh.vertices) == 0:
        return np.empty((0, 3))
    # obj.matrix_world is a 4x4 mathutils.Matrix; numpy's `@` can't multiply it
    # directly against an (N, 3) array, so the rotation/scale submatrix and
    # translation are applied explicitly (same pattern as
    # add_bounding_primitive.set_origin_to_center_of_mass).
    verts_local = np.array([v.co for v in mesh.vertices])
    mat_world = np.array(obj.matrix_world)
    return verts_local @ mat_world[:3, :3].T + mat_world[:3, 3]


def _world_aabb(obj, depsgraph):
    coords = _world_coords(obj, depsgraph)
    if len(coords) == 0:
        return None
    return coords.min(axis=0), coords.max(axis=0)


_SHAPE_NAMING_PROP = {
    'box_shape': 'box_shape',
    'sphere_shape': 'sphere_shape',
    'capsule_shape': 'capsule_shape',
    'convex_shape': 'convex_shape',
    'mesh_shape': 'mesh_shape',
    'voxel_shape': 'voxel_shape',
}


def check_missing_collider(render_obj, use_parent_to):
    """Flag a render mesh that has no child object marked as a collider."""
    if not use_parent_to:
        return None
    if any(child.get('isCollider') for child in render_obj.children):
        return None
    return ValidationIssue(
        check_id='missing_collider',
        object_name=render_obj.name,
        severity='WARNING',
        message="no collider assigned",
    )


def check_triangle_count(collider_obj, max_triangles, depsgraph):
    """Flag a collider whose evaluated (post-modifier) triangle count is too high."""
    obj_eval = collider_obj.evaluated_get(depsgraph)
    mesh = obj_eval.to_mesh()
    try:
        tri_count = sum(len(p.vertices) - 2 for p in mesh.polygons)
    finally:
        obj_eval.to_mesh_clear()

    if tri_count <= max_triangles:
        return None
    return ValidationIssue(
        check_id='triangle_count',
        object_name=collider_obj.name,
        severity='WARNING',
        message=f"{tri_count} triangles (limit {max_triangles})",
    )


def check_min_dimension(collider_obj, min_dimension):
    """Flag a collider whose local-space bounding box is smaller than expected.

    Unlike check_triangle_count/check_non_manifold/check_flipped_normals, this
    intentionally reads collider_obj.data directly rather than the evaluated
    (post-modifier) mesh: min-dimension is meant to catch a collider whose
    *authored* geometry is degenerate, which a Mirror/Array/Solidify modifier
    could otherwise mask (e.g. a zero-thickness plane that only becomes solid
    after a Solidify modifier is applied at export/bake time)."""
    size = mesh_max_dimension(collider_obj.data)
    if size >= min_dimension:
        return None
    return ValidationIssue(
        check_id='min_dimension',
        object_name=collider_obj.name,
        severity='WARNING',
        message=f"max dimension {size:.4f} is below {min_dimension:.4f}",
    )


def check_bbox_mismatch(render_obj, collider_objs, tolerance, depsgraph):
    """Flag a render mesh whose colliders, taken together, don't cover its
    world-space bounding box: the *combined* (union) bbox of every collider
    in `collider_objs` is compared against the render mesh's own bbox.
    Several colliders commonly combine to represent one render mesh's shape
    (e.g. a torso box plus limb capsules) - comparing each one individually
    against the full mesh would flag nearly every compound setup as a
    "mismatch" even when it's correct, so they're considered as a whole."""
    render_aabb = _world_aabb(render_obj, depsgraph)
    if render_aabb is None:
        return None

    collider_aabbs = [aabb for c in collider_objs if (aabb := _world_aabb(c, depsgraph)) is not None]
    if not collider_aabbs:
        return None

    c_min = np.min([aabb[0] for aabb in collider_aabbs], axis=0)
    c_max = np.max([aabb[1] for aabb in collider_aabbs], axis=0)
    r_min, r_max = render_aabb
    render_diag = float(np.linalg.norm(r_max - r_min))
    if render_diag == 0:
        return None

    delta = max(float(np.max(np.abs(c_min - r_min))), float(np.max(np.abs(c_max - r_max))))
    if delta <= tolerance * render_diag:
        return None
    return ValidationIssue(
        check_id='bbox_mismatch',
        object_name=render_obj.name,
        severity='WARNING',
        message=f"combined collider bounding box differs from this mesh's by {delta:.4f}",
    )


def check_too_many_colliders(render_obj, max_colliders):
    """Flag a render mesh with more collider children than `max_colliders` -
    a large number of collider shapes on one object can hurt physics
    performance and often signals the setup could be simplified or merged."""
    collider_count = sum(1 for child in render_obj.children if child.get('isCollider'))
    if collider_count <= max_colliders:
        return None
    return ValidationIssue(
        check_id='too_many_colliders',
        object_name=render_obj.name,
        severity='WARNING',
        message=f"{collider_count} collider shapes assigned (limit {max_colliders})",
    )


def check_naming_convention(collider_obj, prefs):
    """Flag a collider whose name doesn't match the naming convention implied
    by its stored shape type."""
    shape = collider_obj.get('collider_shape')
    prop_name = _SHAPE_NAMING_PROP.get(shape)
    if prop_name is None:
        return None

    shape_str = getattr(prefs, prop_name)
    if not shape_str:
        # Nothing configured for this shape (e.g. default mesh_shape == ""), so
        # there is no naming convention to enforce.
        return None

    separator = re.escape(prefs.separator)
    pattern = re.compile(fr'(^|{separator}){re.escape(shape_str)}({separator}|$)', re.IGNORECASE)
    if pattern.search(collider_obj.name):
        return None
    return ValidationIssue(
        check_id='naming',
        object_name=collider_obj.name,
        severity='WARNING',
        message=f"name doesn't match the '{shape_str}' naming convention",
    )


def check_non_manifold(collider_obj, depsgraph):
    """Flag a collider with edges that aren't shared by exactly two faces."""
    obj_eval = collider_obj.evaluated_get(depsgraph)
    mesh = obj_eval.to_mesh()
    try:
        bm = bmesh.new()
        bm.from_mesh(mesh)
        non_manifold_count = sum(1 for e in bm.edges if not e.is_manifold)
        bm.free()
    finally:
        obj_eval.to_mesh_clear()

    if non_manifold_count == 0:
        return None
    return ValidationIssue(
        check_id='non_manifold',
        object_name=collider_obj.name,
        severity='ERROR',
        message=f"{non_manifold_count} non-manifold edge(s)",
    )


def check_flipped_normals(collider_obj, depsgraph):
    """Flag a collider whose overall face winding is inverted (inside-out
    mesh). Only meaningful for a closed mesh - the sign of the volume isn't
    well-defined for a non-manifold/open surface, so those are skipped."""
    obj_eval = collider_obj.evaluated_get(depsgraph)
    mesh = obj_eval.to_mesh()
    try:
        bm = bmesh.new()
        bm.from_mesh(mesh)
        if any(not e.is_manifold for e in bm.edges):
            bm.free()
            return None
        volume = bm.calc_volume(signed=True)
        bm.free()
    finally:
        obj_eval.to_mesh_clear()

    if volume >= 0:
        return None
    return ValidationIssue(
        check_id='flipped_normals',
        object_name=collider_obj.name,
        severity='ERROR',
        message="faces appear flipped (inside-out mesh)",
    )


@dataclass(frozen=True)
class _ShapeMetrics:
    mesh_volume: float
    hull_volume: float
    obb_volume: 'float | None'  # None if a minimum bounding box couldn't be derived


def _convex_hull_metrics(local_verts):
    """Build the convex hull of `local_verts` as a scratch bmesh (the same
    vert-only-then-convex_hull-then-delete-unused pattern already used in
    add_bounding_convex_hull.py) and return (hull_volume, hull_vert_count,
    min_obb_volume). The minimum-volume oriented bounding box is computed via
    the same rotating-calipers approach as the Oriented Minimum BBox operator
    (add_minimum_bounding_box.py), reusing its pure `rotating_calipers`
    static method directly rather than the full obj_rotating_calipers
    classmethod, which additionally creates real bpy.data mesh/object side
    effects we don't want from a read-only check."""
    bm = bmesh.new()
    for co in local_verts:
        bm.verts.new(co)
    hull = bmesh.ops.convex_hull(bm, input=bm.verts)
    bmesh.ops.delete(bm, geom=hull['geom_unused'], context='VERTS')
    bm.verts.ensure_lookup_table()

    hull_volume = abs(bm.calc_volume(signed=False))
    hull_vert_count = len(bm.verts)
    hull_points = np.array([v.co for v in bm.verts])

    bases = []
    for face in bm.faces:
        if len(face.verts) != 3:
            continue
        face_normal = face.normal
        if np.allclose(face_normal, 0, atol=0.00001):
            continue
        for e in face.edges:
            v0, v1 = e.verts
            edge_vec = (v0.co - v1.co).normalized()
            co_tangent = face_normal.cross(edge_vec)
            bases.append((edge_vec, co_tangent, face_normal))

    obb_volume = None
    if bases:
        _, bb_max, bb_min = OBJECT_OT_add_aligned_bounding_box.rotating_calipers(hull_points, bases)
        if bb_min is not None and bb_max is not None:
            obb_volume = float(np.prod(bb_max - bb_min))

    bm.free()
    return hull_volume, hull_vert_count, obb_volume


def _shape_metrics(collider_obj, depsgraph):
    """Volume-based shape metrics for `collider_obj`'s evaluated mesh, or
    None if the mesh isn't a closed manifold with nonzero volume (the ratios
    the box/convexity checks build on aren't meaningful otherwise)."""
    obj_eval = collider_obj.evaluated_get(depsgraph)
    mesh = obj_eval.to_mesh()
    try:
        if len(mesh.vertices) < 4:
            return None
        bm = bmesh.new()
        bm.from_mesh(mesh)
        if any(not e.is_manifold for e in bm.edges):
            bm.free()
            return None
        mesh_volume = abs(bm.calc_volume(signed=False))
        bm.free()
        if mesh_volume == 0:
            return None
        local_verts = [v.co.copy() for v in mesh.vertices]
    finally:
        obj_eval.to_mesh_clear()

    hull_volume, _, obb_volume = _convex_hull_metrics(local_verts)
    if hull_volume == 0:
        return None
    return _ShapeMetrics(mesh_volume=mesh_volume, hull_volume=hull_volume, obb_volume=obb_volume)


def check_convexity_mismatch(collider_obj, depsgraph, tolerance=0.02):
    """Flag a collider marked convex_shape whose geometry isn't actually
    convex: its own volume differs from its convex hull's volume by more
    than `tolerance` (a convex mesh's volume always equals its hull's)."""
    if collider_obj.get('collider_shape') != 'convex_shape':
        return None

    metrics = _shape_metrics(collider_obj, depsgraph)
    if metrics is None:
        return None

    if (metrics.hull_volume - metrics.mesh_volume) / metrics.hull_volume <= tolerance:
        return None
    return ValidationIssue(
        check_id='convex_shape_mismatch',
        object_name=collider_obj.name,
        severity='WARNING',
        message="marked as convex but its geometry is not convex",
    )


def check_box_mismatch(collider_obj, depsgraph, tolerance=0.02):
    """Flag a collider marked box_shape whose geometry isn't actually a box:
    its convex hull's volume differs from its minimum oriented bounding
    box's volume by more than `tolerance` (a box's hull volume always equals
    its own minimum OBB volume)."""
    if collider_obj.get('collider_shape') != 'box_shape':
        return None

    metrics = _shape_metrics(collider_obj, depsgraph)
    if metrics is None or metrics.obb_volume is None:
        return None

    if (metrics.obb_volume - metrics.hull_volume) / metrics.obb_volume <= tolerance:
        return None
    return ValidationIssue(
        check_id='box_shape_mismatch',
        object_name=collider_obj.name,
        severity='WARNING',
        message="marked as a box but its geometry is not box-shaped",
    )


def check_mesh_could_use_primitive(collider_obj, depsgraph, tolerance=0.02):
    """Flag a mesh_shape collider whose geometry is already convex (or even
    box-shaped) - a simpler, cheaper primitive collider would describe the
    same volume just as accurately."""
    if collider_obj.get('collider_shape') != 'mesh_shape':
        return None

    metrics = _shape_metrics(collider_obj, depsgraph)
    if metrics is None:
        return None

    is_convex = (metrics.hull_volume - metrics.mesh_volume) / metrics.hull_volume <= tolerance
    if not is_convex:
        return None

    is_box = (
        metrics.obb_volume is not None
        and (metrics.obb_volume - metrics.hull_volume) / metrics.obb_volume <= tolerance
    )
    suggestion = 'box' if is_box else 'convex hull'
    return ValidationIssue(
        check_id='mesh_could_use_primitive',
        object_name=collider_obj.name,
        severity='WARNING',
        message=f"geometry is convex, a {suggestion} collider would be simpler and cheaper",
    )


@dataclass(frozen=True)
class _RenderMeshShapeMetrics:
    mesh_volume: float
    hull_volume: float
    obb_volume: 'float | None'
    sphere_volume: float


def _render_mesh_shape_metrics(render_obj, depsgraph):
    """World-space volume-based shape metrics for a render mesh, or None if
    it isn't a closed manifold with nonzero volume. Deliberately world-space
    (unlike _shape_metrics, which is local-space and transform-invariant by
    design): a non-uniformly-scaled render mesh genuinely looks different in
    the scene than its raw mesh data suggests, matching the same reasoning
    check_bbox_mismatch already applies. Uses to_mesh()/to_mesh_clear()
    rather than _world_coords, since _world_coords reads `.data.vertices`
    directly, which would raise on a CURVE/SURFACE/FONT/META render-mesh
    parent (all valid per VALID_OBJECT_TYPES)."""
    obj_eval = render_obj.evaluated_get(depsgraph)
    mesh = obj_eval.to_mesh()
    try:
        if len(mesh.vertices) < 4:
            return None
        bm = bmesh.new()
        bm.from_mesh(mesh)
        if any(not e.is_manifold for e in bm.edges):
            bm.free()
            return None
        mesh_volume = abs(bm.calc_volume(signed=False))
        bm.free()
        if mesh_volume == 0:
            return None

        mat_world = np.array(render_obj.matrix_world)
        local_verts = np.array([v.co for v in mesh.vertices])
        world_verts = local_verts @ mat_world[:3, :3].T + mat_world[:3, 3]

        _, sphere_radius = OBJECT_OT_add_bounding_sphere.calculate_bounding_sphere(render_obj, mesh.vertices)
    finally:
        obj_eval.to_mesh_clear()

    hull_volume, _, obb_volume = _convex_hull_metrics(world_verts)
    if hull_volume == 0:
        return None

    return _RenderMeshShapeMetrics(
        mesh_volume=mesh_volume,
        hull_volume=hull_volume,
        obb_volume=obb_volume,
        sphere_volume=(4.0 / 3.0) * np.pi * sphere_radius ** 3,
    )


def _classify_render_mesh_shape(metrics, shape_tolerance, sphere_tolerance):
    """Best-fit primitive for a render mesh's shape metrics: 'box', 'sphere',
    'convex', or None if it's concave/complex enough that no single
    primitive is "the right one" to demand. is_box/is_sphere are both gated
    on is_convex so a concave shape can't be misclassified as sphere-like by
    volume coincidence."""
    if metrics is None:
        return None

    is_convex = (metrics.hull_volume - metrics.mesh_volume) / metrics.hull_volume <= shape_tolerance
    if not is_convex:
        return None

    is_box = (
        metrics.obb_volume is not None
        and (metrics.obb_volume - metrics.hull_volume) / metrics.obb_volume <= shape_tolerance
    )
    if is_box:
        return 'box'

    is_sphere = (
        metrics.sphere_volume > 0
        and (metrics.sphere_volume - metrics.mesh_volume) / metrics.sphere_volume <= sphere_tolerance
    )
    if is_sphere:
        return 'sphere'

    return 'convex'


_SHAPE_TO_BEST_FIT = {
    'box_shape': 'box',
    'sphere_shape': 'sphere',
    'convex_shape': 'convex',
}
_BEST_FIT_LABEL = {'box': 'box', 'sphere': 'sphere', 'convex': 'convex hull'}


def check_collision_shape_mismatch(collider_obj, depsgraph, shape_tolerance=0.02, sphere_tolerance=0.05):
    """Flag a collider whose assigned shape (box/sphere/convex hull) doesn't
    suit the shape of its render mesh - e.g. a box collider on a ball-like
    mesh. Unlike check_box_mismatch/check_convexity_mismatch (which check a
    collider's self-consistency with its own claimed shape), this compares
    against the render mesh it was generated from. capsule_shape/mesh_shape/
    voxel_shape are never evaluated: there is no reliable capsule/cylinder-
    likeness test, and mesh/voxel colliders are detailed approximations that
    are never "wrong" by definition."""
    shape = collider_obj.get('collider_shape')
    expected_fit = _SHAPE_TO_BEST_FIT.get(shape)
    if expected_fit is None:
        return None

    parent = collider_obj.parent
    if parent is None or parent.get('isCollider') or parent.type not in VALID_OBJECT_TYPES:
        # check_parent_hierarchy already owns reporting a broken/missing parent.
        return None

    metrics = _render_mesh_shape_metrics(parent, depsgraph)
    best_fit = _classify_render_mesh_shape(metrics, shape_tolerance, sphere_tolerance)
    if best_fit is None or best_fit == expected_fit:
        return None
    if expected_fit == 'convex':
        # Every reachable best_fit is convex-compatible by construction (box
        # and sphere are both gated on is_convex above), so a convex_shape
        # collider can never actually land here - kept for completeness.
        return None

    return ValidationIssue(
        check_id='collision_shape_mismatch',
        object_name=collider_obj.name,
        severity='WARNING',
        message=(f"marked as '{_BEST_FIT_LABEL[expected_fit]}' but its render mesh "
                 f"'{parent.name}' looks {_BEST_FIT_LABEL[best_fit]}-like"),
    )


def check_physics_material(collider_obj):
    """Flag a collider with no material tagged as a physics material."""
    materials = collider_obj.data.materials
    if any(mat is not None and getattr(mat, 'isPhysicsMaterial', False) for mat in materials):
        return None
    return ValidationIssue(
        check_id='physics_material',
        object_name=collider_obj.name,
        severity='WARNING',
        message="no physics material assigned",
    )


def check_parent_hierarchy(collider_obj, use_parent_to):
    """Flag a collider that isn't parented to a plausible render mesh."""
    if not use_parent_to:
        return None

    parent = collider_obj.parent
    if parent is None:
        return ValidationIssue(
            check_id='parent_hierarchy',
            object_name=collider_obj.name,
            severity='WARNING',
            message="not parented to a render mesh",
        )
    if parent.get('isCollider'):
        return ValidationIssue(
            check_id='parent_hierarchy',
            object_name=collider_obj.name,
            severity='WARNING',
            message=f"parented to another collider ('{parent.name}')",
        )
    if parent.type not in VALID_OBJECT_TYPES:
        return ValidationIssue(
            check_id='parent_hierarchy',
            object_name=collider_obj.name,
            severity='WARNING',
            message=f"parent '{parent.name}' is not a valid render mesh type",
        )
    return None


def collect_validation_issues(objects, prefs, depsgraph, progress_callback=None):
    """Run every enabled check over `objects` and return the list of issues found.

    A check raising on one object (e.g. malformed custom properties, an
    unexpected mesh state) is reported as its own issue rather than aborting
    the whole scan, so one bad object can't hide results for everything else.
    `progress_callback`, if given, is called with (done_count, total_count)
    after each object is processed - used by the operator to drive a
    wm.progress_begin/update/end bar on large scenes.
    """
    issues = []
    objects = list(objects)

    for index, obj in enumerate(objects):
        try:
            issues.extend(_collect_object_issues(obj, prefs, depsgraph))
        except Exception as exc:
            issues.append(ValidationIssue(
                check_id='internal_error',
                object_name=obj.name,
                severity='ERROR',
                message=f"validation check failed on this object: {exc}",
            ))
        finally:
            if progress_callback is not None:
                progress_callback(index + 1, len(objects))

    return issues


def _collect_object_issues(obj, prefs, depsgraph):
    """Run every enabled check against a single object. Split out of
    collect_validation_issues() so a raise here is caught per-object."""
    issues = []
    is_collider = bool(obj.get('isCollider'))

    if not is_collider:
        if obj.type in VALID_OBJECT_TYPES:
            if prefs.validate_check_missing_collider:
                issue = check_missing_collider(obj, prefs.use_parent_to)
                if issue:
                    issues.append(issue)

            colliders = [c for c in obj.children if c.get('isCollider')]
            if colliders:
                if prefs.validate_check_bbox_mismatch:
                    issue = check_bbox_mismatch(obj, colliders, prefs.validation_bbox_tolerance, depsgraph)
                    if issue:
                        issues.append(issue)

                if prefs.validate_check_too_many_colliders:
                    issue = check_too_many_colliders(obj, prefs.validation_max_collider_count)
                    if issue:
                        issues.append(issue)
        return issues

    if obj.type == 'MESH':
        if prefs.validate_check_triangle_count:
            issue = check_triangle_count(obj, prefs.validation_max_triangle_count, depsgraph)
            if issue:
                issues.append(issue)

        if prefs.validate_check_min_dimension:
            issue = check_min_dimension(obj, prefs.validation_min_dimension)
            if issue:
                issues.append(issue)

        if prefs.validate_check_non_manifold:
            issue = check_non_manifold(obj, depsgraph)
            if issue:
                issues.append(issue)

        if prefs.validate_check_flipped_normals:
            issue = check_flipped_normals(obj, depsgraph)
            if issue:
                issues.append(issue)

        if prefs.validate_check_convex_shape_mismatch:
            issue = check_convexity_mismatch(obj, depsgraph, prefs.validation_shape_tolerance)
            if issue:
                issues.append(issue)

        if prefs.validate_check_box_shape_mismatch:
            issue = check_box_mismatch(obj, depsgraph, prefs.validation_shape_tolerance)
            if issue:
                issues.append(issue)

        if prefs.validate_check_mesh_could_use_primitive:
            issue = check_mesh_could_use_primitive(obj, depsgraph, prefs.validation_shape_tolerance)
            if issue:
                issues.append(issue)

        if prefs.validate_check_collision_shape_mismatch:
            issue = check_collision_shape_mismatch(
                obj, depsgraph, prefs.validation_shape_tolerance, prefs.validation_sphere_tolerance,
            )
            if issue:
                issues.append(issue)

        if prefs.validate_check_physics_material:
            issue = check_physics_material(obj)
            if issue:
                issues.append(issue)

    if prefs.validate_check_naming:
        issue = check_naming_convention(obj, prefs)
        if issue:
            issues.append(issue)

    if prefs.validate_check_parent_hierarchy:
        issue = check_parent_hierarchy(obj, prefs.use_parent_to)
        if issue:
            issues.append(issue)

    return issues
