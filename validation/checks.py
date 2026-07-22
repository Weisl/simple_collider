import re
from dataclasses import dataclass

import bmesh
import numpy as np

from ..bmesh_operations.voxel_generation import mesh_max_dimension
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
        message=f"{render_obj.name}: no collider assigned",
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
        message=f"{collider_obj.name}: {tri_count} triangles (limit {max_triangles})",
    )


def check_min_dimension(collider_obj, min_dimension):
    """Flag a collider whose local-space bounding box is smaller than expected."""
    size = mesh_max_dimension(collider_obj.data)
    if size >= min_dimension:
        return None
    return ValidationIssue(
        check_id='min_dimension',
        object_name=collider_obj.name,
        severity='WARNING',
        message=f"{collider_obj.name}: max dimension {size:.4f} is below {min_dimension:.4f}",
    )


def check_bbox_mismatch(collider_obj, render_obj, tolerance, depsgraph):
    """Flag a collider whose world-space bounding box deviates from its render
    mesh parent's by more than `tolerance` times the render mesh's bbox diagonal."""
    collider_aabb = _world_aabb(collider_obj, depsgraph)
    render_aabb = _world_aabb(render_obj, depsgraph)
    if collider_aabb is None or render_aabb is None:
        return None

    c_min, c_max = collider_aabb
    r_min, r_max = render_aabb
    render_diag = float(np.linalg.norm(r_max - r_min))
    if render_diag == 0:
        return None

    delta = max(float(np.max(np.abs(c_min - r_min))), float(np.max(np.abs(c_max - r_max))))
    if delta <= tolerance * render_diag:
        return None
    return ValidationIssue(
        check_id='bbox_mismatch',
        object_name=collider_obj.name,
        severity='WARNING',
        message=f"{collider_obj.name}: bounding box differs from '{render_obj.name}' by {delta:.4f}",
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

    separator = prefs.separator
    pattern = re.compile(fr'(^|{separator}){shape_str}({separator}|$)', re.IGNORECASE)
    if pattern.search(collider_obj.name):
        return None
    return ValidationIssue(
        check_id='naming',
        object_name=collider_obj.name,
        severity='WARNING',
        message=f"{collider_obj.name}: name doesn't match the '{shape_str}' naming convention",
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
        message=f"{collider_obj.name}: {non_manifold_count} non-manifold edge(s)",
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
        message=f"{collider_obj.name}: no physics material assigned",
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
            message=f"{collider_obj.name}: not parented to a render mesh",
        )
    if parent.get('isCollider'):
        return ValidationIssue(
            check_id='parent_hierarchy',
            object_name=collider_obj.name,
            severity='WARNING',
            message=f"{collider_obj.name}: parented to another collider ('{parent.name}')",
        )
    if parent.type not in VALID_OBJECT_TYPES:
        return ValidationIssue(
            check_id='parent_hierarchy',
            object_name=collider_obj.name,
            severity='WARNING',
            message=f"{collider_obj.name}: parent '{parent.name}' is not a valid render mesh type",
        )
    return None


def collect_validation_issues(objects, prefs, depsgraph):
    """Run every enabled check over `objects` and return the list of issues found."""
    issues = []

    for obj in objects:
        is_collider = bool(obj.get('isCollider'))

        if not is_collider:
            if obj.type == 'MESH' and prefs.validate_check_missing_collider:
                issue = check_missing_collider(obj, prefs.use_parent_to)
                if issue:
                    issues.append(issue)
            continue

        if obj.type == 'MESH':
            if prefs.validate_check_triangle_count:
                issue = check_triangle_count(obj, prefs.validation_max_triangle_count, depsgraph)
                if issue:
                    issues.append(issue)

            if prefs.validate_check_min_dimension:
                issue = check_min_dimension(obj, prefs.validation_min_dimension)
                if issue:
                    issues.append(issue)

            if prefs.validate_check_bbox_mismatch and obj.parent is not None:
                issue = check_bbox_mismatch(obj, obj.parent, prefs.validation_bbox_tolerance, depsgraph)
                if issue:
                    issues.append(issue)

            if prefs.validate_check_non_manifold:
                issue = check_non_manifold(obj, depsgraph)
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
