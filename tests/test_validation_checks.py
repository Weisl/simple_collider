"""Unit tests for the collider validation checks (validation/checks.py).

Run with headless Blender::

    blender --background --python tests/test_validation_checks.py
"""
import os
import sys
import unittest
from types import SimpleNamespace

import bmesh
import bpy
from mathutils import Matrix

# Make the add-on importable as a package.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ADDON_NAME = os.path.basename(_PROJECT_ROOT)
sys.path.insert(0, os.path.dirname(_PROJECT_ROOT))

_addon = __import__(_ADDON_NAME)
_checks = _addon.validation.checks
_CollisionAddonPrefs = _addon.preferences.preferences.CollisionAddonPrefs

# -- Helpers -----------------------------------------------------------------

_TEST_PREFIX = 'validation_test_'

# Unit cube face indices (see _make_cube_object). Dropping faces from the end
# of this list leaves the box open on the +Z side, which is what makes
# check_non_manifold flag it.
_CUBE_FACES = (
    (0, 1, 3, 2),  # -X
    (4, 6, 7, 5),  # +X
    (0, 4, 5, 1),  # -Y
    (2, 3, 7, 6),  # +Y
    (0, 2, 6, 4),  # -Z
    (1, 5, 7, 3),  # +Z
)


def _make_mesh_object(name, verts, faces):
    mesh = bpy.data.meshes.new(name + '_data')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def _make_cube_object(name, half_extent=1.0, face_count=6, matrix_world=None):
    """A cube centred on the origin (before `matrix_world`) with the first
    `face_count` faces of _CUBE_FACES. face_count=6 is a closed, manifold
    cube; face_count<6 leaves it open (non-manifold boundary edges)."""
    h = half_extent
    verts = [
        (-h, -h, -h), (-h, -h, h), (-h, h, -h), (-h, h, h),
        (h, -h, -h), (h, -h, h), (h, h, -h), (h, h, h),
    ]
    obj = _make_mesh_object(name, verts, _CUBE_FACES[:face_count])
    if matrix_world is not None:
        obj.matrix_world = matrix_world
    return obj


def _make_box_object(name, half_extents, matrix_world=None):
    """A closed box with independent half-extents per axis, for building
    colliders that only cover part of a render mesh along one axis (e.g. a
    "left half" / "right half" pair) while matching it fully on the others."""
    hx, hy, hz = half_extents
    verts = [
        (-hx, -hy, -hz), (-hx, -hy, hz), (-hx, hy, -hz), (-hx, hy, hz),
        (hx, -hy, -hz), (hx, -hy, hz), (hx, hy, -hz), (hx, hy, hz),
    ]
    obj = _make_mesh_object(name, verts, _CUBE_FACES)
    if matrix_world is not None:
        obj.matrix_world = matrix_world
    return obj


def _make_tetrahedron_object(name, matrix_world=None):
    """Regular tetrahedron inscribed in a cube of half-extent 1 (verts at
    alternating cube corners) - a simple closed, convex, manifold shape
    whose minimum bounding box is far larger than its own volume, useful for
    testing the 'is this actually box-shaped' heuristic."""
    verts = [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]
    faces = [(0, 1, 2), (0, 3, 1), (0, 2, 3), (1, 3, 2)]
    obj = _make_mesh_object(name, verts, faces)
    if matrix_world is not None:
        obj.matrix_world = matrix_world
    return obj


def _make_dented_cube_object(name):
    """A cube with a pyramidal dent pressed into the +Z face - closed,
    manifold, and clearly non-convex (its convex hull reconstructs the flat
    top that the dent removes material from)."""
    h = 1.0
    verts = [
        (-h, -h, -h), (-h, -h, h), (-h, h, -h), (-h, h, h),
        (h, -h, -h), (h, -h, h), (h, h, -h), (h, h, h),
        (0.0, 0.0, 0.5),  # pulled-in center of the +Z face
    ]
    faces = [
        (0, 1, 3, 2),  # -X
        (4, 6, 7, 5),  # +X
        (0, 4, 5, 1),  # -Y
        (2, 3, 7, 6),  # +Y
        (0, 2, 6, 4),  # -Z
        # +Z face (1, 5, 7, 3) replaced by a fan around the dented center (8)
        (1, 5, 8),
        (5, 7, 8),
        (7, 3, 8),
        (3, 1, 8),
    ]
    return _make_mesh_object(name, verts, faces)


def _remove_test_objects():
    for obj in list(bpy.data.objects):
        if obj.name.startswith(_TEST_PREFIX):
            data = obj.data
            bpy.data.objects.remove(obj)
            if isinstance(data, bpy.types.Mesh):
                bpy.data.meshes.remove(data)
            elif isinstance(data, bpy.types.Curve):
                bpy.data.curves.remove(data)


def _make_fake_prefs(**overrides):
    """A minimal stand-in for CollisionAddonPrefs covering every attribute
    collect_validation_issues()/check_naming_convention() read, without
    needing the real preferences class registered on bpy.context. Every
    validate_check_* toggle defaults to False so a test only has to turn on
    the one(s) it actually exercises."""
    defaults = dict(
        use_parent_to=True,
        validate_check_missing_collider=False,
        validate_check_bbox_mismatch=False,
        validate_check_too_many_colliders=False,
        validate_check_triangle_count=False,
        validate_check_min_dimension=False,
        validate_check_non_manifold=False,
        validate_check_flipped_normals=False,
        validate_check_convex_shape_mismatch=False,
        validate_check_box_shape_mismatch=False,
        validate_check_mesh_could_use_primitive=False,
        validate_check_collision_shape_mismatch=False,
        validate_check_physics_material=False,
        validate_check_naming=False,
        validate_check_parent_hierarchy=False,
        validate_check_parent_inverse_matrix=False,
        validation_bbox_tolerance=0.1,
        validation_max_collider_count=8,
        validation_max_triangle_count=100000,
        validation_min_dimension=0.0,
        validation_shape_tolerance=0.02,
        validation_sphere_tolerance=0.05,
        separator='_',
        box_shape='UBX',
        sphere_shape='USP',
        capsule_shape='UCP',
        convex_shape='UCX',
        mesh_shape='',
        voxel_shape='UVX',
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _remove_test_materials():
    for mat in list(bpy.data.materials):
        if mat.name.startswith(_TEST_PREFIX):
            bpy.data.materials.remove(mat)


def _depsgraph():
    return bpy.context.evaluated_depsgraph_get()


def _make_uv_sphere_render(name, radius=1.0):
    """A well-tessellated UV sphere, tagged with the test prefix so it's
    caught by _remove_test_objects(). Used as a convincing "actually looks
    round" render mesh for check_collision_shape_mismatch."""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=32, ring_count=16)
    obj = bpy.context.active_object
    obj.name = name
    return obj


def _make_cylinder_render(name, radius=1.0, depth=2.0):
    """A well-tessellated cylinder - convex, but neither box- nor
    sphere-shaped, so it should classify as generic 'convex'."""
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, vertices=32)
    obj = bpy.context.active_object
    obj.name = name
    return obj


# -- Geometry-only checks (no preferences involved) ---------------------------

class TestGeometryChecks(unittest.TestCase):
    """check_triangle_count, check_min_dimension, check_non_manifold and
    check_bbox_mismatch only need mesh/object data, no addon preferences."""

    def tearDown(self):
        _remove_test_objects()

    def test_triangle_count_pass(self):
        # A closed cube triangulates to 6 quads * 2 tris = 12 tris.
        obj = _make_cube_object(_TEST_PREFIX + 'cube')
        obj['collider_shape'] = 'mesh_shape'
        issue = _checks.check_triangle_count(obj, max_triangles=12, depsgraph=_depsgraph())
        self.assertIsNone(issue)

    def test_triangle_count_flagged(self):
        obj = _make_cube_object(_TEST_PREFIX + 'cube')
        obj['collider_shape'] = 'mesh_shape'
        issue = _checks.check_triangle_count(obj, max_triangles=5, depsgraph=_depsgraph())
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'triangle_count')
        self.assertEqual(issue.object_name, obj.name)

    def test_triangle_count_flagged_for_convex_shape(self):
        obj = _make_cube_object(_TEST_PREFIX + 'cube')
        obj['collider_shape'] = 'convex_shape'
        issue = _checks.check_triangle_count(obj, max_triangles=5, depsgraph=_depsgraph())
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'triangle_count')

    def test_triangle_count_skipped_for_box_shape(self):
        # box/sphere/capsule/voxel colliders are simple analytical shapes;
        # a high triangle count on their authored geometry isn't meaningful.
        obj = _make_cube_object(_TEST_PREFIX + 'cube')
        obj['collider_shape'] = 'box_shape'
        issue = _checks.check_triangle_count(obj, max_triangles=5, depsgraph=_depsgraph())
        self.assertIsNone(issue)

    def test_min_dimension_pass(self):
        obj = _make_cube_object(_TEST_PREFIX + 'cube', half_extent=1.0)  # extent 2
        issue = _checks.check_min_dimension(obj, min_dimension=1.0)
        self.assertIsNone(issue)

    def test_min_dimension_flagged(self):
        obj = _make_cube_object(_TEST_PREFIX + 'cube', half_extent=1.0)  # extent 2
        issue = _checks.check_min_dimension(obj, min_dimension=5.0)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'min_dimension')

    def test_non_manifold_pass_closed_cube(self):
        obj = _make_cube_object(_TEST_PREFIX + 'cube', face_count=6)
        issue = _checks.check_non_manifold(obj, depsgraph=_depsgraph())
        self.assertIsNone(issue)

    def test_non_manifold_flagged_open_cube(self):
        obj = _make_cube_object(_TEST_PREFIX + 'cube', face_count=5)
        issue = _checks.check_non_manifold(obj, depsgraph=_depsgraph())
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'non_manifold')

    def test_bbox_mismatch_pass_when_aligned(self):
        render_obj = _make_cube_object(_TEST_PREFIX + 'render', half_extent=1.0)
        collider_obj = _make_cube_object(_TEST_PREFIX + 'collider', half_extent=1.0)
        issue = _checks.check_bbox_mismatch(render_obj, [collider_obj], tolerance=0.1, depsgraph=_depsgraph())
        self.assertIsNone(issue)

    def test_bbox_mismatch_flagged_when_offset(self):
        render_obj = _make_cube_object(_TEST_PREFIX + 'render', half_extent=1.0)
        collider_obj = _make_cube_object(
            _TEST_PREFIX + 'collider', half_extent=1.0,
            matrix_world=Matrix.Translation((1.0, 0.0, 0.0)),
        )
        issue = _checks.check_bbox_mismatch(render_obj, [collider_obj], tolerance=0.1, depsgraph=_depsgraph())
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'bbox_mismatch')
        self.assertEqual(issue.object_name, render_obj.name)

    def test_bbox_mismatch_pass_with_multiple_partial_colliders(self):
        """Two colliders that individually only cover half the render mesh
        along one axis, but whose combined (union) bbox matches it fully -
        must NOT be flagged, since colliders are considered together."""
        render_obj = _make_cube_object(_TEST_PREFIX + 'render', half_extent=2.0)  # extent -2..2 all axes
        left = _make_box_object(_TEST_PREFIX + 'left', half_extents=(1.0, 2.0, 2.0),
                                matrix_world=Matrix.Translation((-1.0, 0.0, 0.0)))  # covers x in [-2, 0]
        right = _make_box_object(_TEST_PREFIX + 'right', half_extents=(1.0, 2.0, 2.0),
                                 matrix_world=Matrix.Translation((1.0, 0.0, 0.0)))  # covers x in [0, 2]
        issue = _checks.check_bbox_mismatch(render_obj, [left, right], tolerance=0.1, depsgraph=_depsgraph())
        self.assertIsNone(issue)

    def test_bbox_mismatch_flagged_when_combined_still_off(self):
        render_obj = _make_cube_object(_TEST_PREFIX + 'render', half_extent=2.0)
        small = _make_cube_object(_TEST_PREFIX + 'small', half_extent=0.5)
        issue = _checks.check_bbox_mismatch(render_obj, [small], tolerance=0.1, depsgraph=_depsgraph())
        self.assertIsNotNone(issue)

    # -- check_too_many_colliders ---------------------------------------------

    def test_too_many_colliders_pass(self):
        render_obj = _make_cube_object(_TEST_PREFIX + 'render')
        for i in range(3):
            collider = _make_cube_object(_TEST_PREFIX + f'collider_{i}')
            collider['isCollider'] = True
            collider.parent = render_obj
        issue = _checks.check_too_many_colliders(render_obj, max_colliders=8)
        self.assertIsNone(issue)

    def test_too_many_colliders_flagged(self):
        render_obj = _make_cube_object(_TEST_PREFIX + 'render')
        for i in range(5):
            collider = _make_cube_object(_TEST_PREFIX + f'collider_{i}')
            collider['isCollider'] = True
            collider.parent = render_obj
        issue = _checks.check_too_many_colliders(render_obj, max_colliders=3)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'too_many_colliders')

    # -- check_flipped_normals ---------------------------------------------

    def test_flipped_normals_pass(self):
        bpy.ops.mesh.primitive_cube_add(size=2)
        obj = bpy.context.active_object
        obj.name = _TEST_PREFIX + 'cube'
        issue = _checks.check_flipped_normals(obj, depsgraph=_depsgraph())
        self.assertIsNone(issue)

    def test_flipped_normals_flagged(self):
        bpy.ops.mesh.primitive_cube_add(size=2)
        obj = bpy.context.active_object
        obj.name = _TEST_PREFIX + 'cube'
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        issue = _checks.check_flipped_normals(obj, depsgraph=_depsgraph())
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'flipped_normals')

    def test_flipped_normals_skipped_when_non_manifold(self):
        obj = _make_cube_object(_TEST_PREFIX + 'cube', face_count=5)
        issue = _checks.check_flipped_normals(obj, depsgraph=_depsgraph())
        self.assertIsNone(issue)

    # -- check_convexity_mismatch -------------------------------------------

    def test_convexity_mismatch_pass_for_convex_mesh(self):
        obj = _make_cube_object(_TEST_PREFIX + 'cube')
        obj['collider_shape'] = 'convex_shape'
        issue = _checks.check_convexity_mismatch(obj, depsgraph=_depsgraph(), tolerance=0.02)
        self.assertIsNone(issue)

    def test_convexity_mismatch_flagged_for_non_convex_mesh(self):
        obj = _make_dented_cube_object(_TEST_PREFIX + 'dented_cube')
        obj['collider_shape'] = 'convex_shape'
        issue = _checks.check_convexity_mismatch(obj, depsgraph=_depsgraph(), tolerance=0.02)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'convex_shape_mismatch')

    def test_convexity_mismatch_skipped_when_not_marked_convex(self):
        obj = _make_dented_cube_object(_TEST_PREFIX + 'dented_cube')
        obj['collider_shape'] = 'mesh_shape'
        issue = _checks.check_convexity_mismatch(obj, depsgraph=_depsgraph(), tolerance=0.02)
        self.assertIsNone(issue)

    # -- check_box_mismatch --------------------------------------------------

    def test_box_mismatch_pass_for_box_mesh(self):
        obj = _make_cube_object(_TEST_PREFIX + 'cube')
        obj['collider_shape'] = 'box_shape'
        issue = _checks.check_box_mismatch(obj, depsgraph=_depsgraph(), tolerance=0.02)
        self.assertIsNone(issue)

    def test_box_mismatch_flagged_for_non_box_mesh(self):
        obj = _make_tetrahedron_object(_TEST_PREFIX + 'tetra')
        obj['collider_shape'] = 'box_shape'
        issue = _checks.check_box_mismatch(obj, depsgraph=_depsgraph(), tolerance=0.02)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'box_shape_mismatch')

    def test_box_mismatch_skipped_when_not_marked_box(self):
        obj = _make_tetrahedron_object(_TEST_PREFIX + 'tetra')
        obj['collider_shape'] = 'convex_shape'
        issue = _checks.check_box_mismatch(obj, depsgraph=_depsgraph(), tolerance=0.02)
        self.assertIsNone(issue)

    # -- check_mesh_could_use_primitive --------------------------------------

    def test_mesh_could_use_primitive_flagged_for_box(self):
        obj = _make_cube_object(_TEST_PREFIX + 'cube')
        obj['collider_shape'] = 'mesh_shape'
        issue = _checks.check_mesh_could_use_primitive(obj, depsgraph=_depsgraph(), tolerance=0.02)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'mesh_could_use_primitive')
        self.assertIn('box', issue.message)

    def test_mesh_could_use_primitive_flagged_for_convex_non_box(self):
        obj = _make_tetrahedron_object(_TEST_PREFIX + 'tetra')
        obj['collider_shape'] = 'mesh_shape'
        issue = _checks.check_mesh_could_use_primitive(obj, depsgraph=_depsgraph(), tolerance=0.02)
        self.assertIsNotNone(issue)
        self.assertIn('convex hull', issue.message)

    def test_mesh_could_use_primitive_pass_for_non_convex_mesh(self):
        obj = _make_dented_cube_object(_TEST_PREFIX + 'dented_cube')
        obj['collider_shape'] = 'mesh_shape'
        issue = _checks.check_mesh_could_use_primitive(obj, depsgraph=_depsgraph(), tolerance=0.02)
        self.assertIsNone(issue)

    def test_mesh_could_use_primitive_skipped_when_not_mesh_shape(self):
        obj = _make_cube_object(_TEST_PREFIX + 'cube')
        obj['collider_shape'] = 'box_shape'
        issue = _checks.check_mesh_could_use_primitive(obj, depsgraph=_depsgraph(), tolerance=0.02)
        self.assertIsNone(issue)

    # -- check_collision_shape_mismatch --------------------------------------

    def _mismatch(self, collider):
        return _checks.check_collision_shape_mismatch(
            collider, depsgraph=_depsgraph(), shape_tolerance=0.02, sphere_tolerance=0.05,
        )

    def test_collision_shape_mismatch_flagged_box_on_sphere_render(self):
        render_obj = _make_uv_sphere_render(_TEST_PREFIX + 'sphere_render')
        collider = _make_cube_object(_TEST_PREFIX + 'collider')
        collider.parent = render_obj
        collider['collider_shape'] = 'box_shape'
        issue = self._mismatch(collider)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'collision_shape_mismatch')
        self.assertIn('box', issue.message)
        self.assertIn('sphere', issue.message)

    def test_collision_shape_mismatch_flagged_sphere_on_box_render(self):
        render_obj = _make_cube_object(_TEST_PREFIX + 'box_render')
        collider = _make_cube_object(_TEST_PREFIX + 'collider')
        collider.parent = render_obj
        collider['collider_shape'] = 'sphere_shape'
        issue = self._mismatch(collider)
        self.assertIsNotNone(issue)

    def test_collision_shape_mismatch_pass_matching_sphere(self):
        render_obj = _make_uv_sphere_render(_TEST_PREFIX + 'sphere_render')
        collider = _make_cube_object(_TEST_PREFIX + 'collider')
        collider.parent = render_obj
        collider['collider_shape'] = 'sphere_shape'
        issue = self._mismatch(collider)
        self.assertIsNone(issue)

    def test_collision_shape_mismatch_pass_matching_box(self):
        render_obj = _make_cube_object(_TEST_PREFIX + 'box_render')
        collider = _make_cube_object(_TEST_PREFIX + 'collider')
        collider.parent = render_obj
        collider['collider_shape'] = 'box_shape'
        issue = self._mismatch(collider)
        self.assertIsNone(issue)

    def test_collision_shape_mismatch_pass_convex_on_cylinder_render(self):
        render_obj = _make_cylinder_render(_TEST_PREFIX + 'cylinder_render')
        collider = _make_cube_object(_TEST_PREFIX + 'collider')
        collider.parent = render_obj
        collider['collider_shape'] = 'convex_shape'
        issue = self._mismatch(collider)
        self.assertIsNone(issue)

    def test_collision_shape_mismatch_flagged_box_on_cylinder_render(self):
        render_obj = _make_cylinder_render(_TEST_PREFIX + 'cylinder_render')
        collider = _make_cube_object(_TEST_PREFIX + 'collider')
        collider.parent = render_obj
        collider['collider_shape'] = 'box_shape'
        issue = self._mismatch(collider)
        self.assertIsNotNone(issue)

    def test_collision_shape_mismatch_pass_convex_never_flagged(self):
        for render_maker, render_name in (
            (_make_cube_object, _TEST_PREFIX + 'box_render'),
            (_make_uv_sphere_render, _TEST_PREFIX + 'sphere_render'),
        ):
            render_obj = render_maker(render_name)
            collider = _make_cube_object(_TEST_PREFIX + 'collider_' + render_name)
            collider.parent = render_obj
            collider['collider_shape'] = 'convex_shape'
            issue = self._mismatch(collider)
            self.assertIsNone(issue)
            _remove_test_objects()

    def test_collision_shape_mismatch_pass_capsule_always_none(self):
        render_obj = _make_uv_sphere_render(_TEST_PREFIX + 'sphere_render')
        collider = _make_cube_object(_TEST_PREFIX + 'collider')
        collider.parent = render_obj
        collider['collider_shape'] = 'capsule_shape'
        issue = self._mismatch(collider)
        self.assertIsNone(issue)

    def test_collision_shape_mismatch_pass_mesh_and_voxel_shape_skipped(self):
        render_obj = _make_uv_sphere_render(_TEST_PREFIX + 'sphere_render')
        for shape in ('mesh_shape', 'voxel_shape'):
            collider = _make_cube_object(_TEST_PREFIX + 'collider_' + shape)
            collider.parent = render_obj
            collider['collider_shape'] = shape
            issue = self._mismatch(collider)
            self.assertIsNone(issue)

    def test_collision_shape_mismatch_pass_no_verdict_on_concave_render(self):
        render_obj = _make_dented_cube_object(_TEST_PREFIX + 'dented_render')
        for shape in ('box_shape', 'sphere_shape'):
            collider = _make_cube_object(_TEST_PREFIX + 'collider_' + shape)
            collider.parent = render_obj
            collider['collider_shape'] = shape
            issue = self._mismatch(collider)
            self.assertIsNone(issue)

    def test_collision_shape_mismatch_pass_no_parent(self):
        collider = _make_cube_object(_TEST_PREFIX + 'collider')
        collider['collider_shape'] = 'box_shape'
        issue = self._mismatch(collider)
        self.assertIsNone(issue)

    def test_collision_shape_mismatch_pass_parent_is_collider(self):
        other_collider = _make_cube_object(_TEST_PREFIX + 'other_collider')
        other_collider['isCollider'] = True
        collider = _make_cube_object(_TEST_PREFIX + 'collider')
        collider.parent = other_collider
        collider['collider_shape'] = 'box_shape'
        issue = self._mismatch(collider)
        self.assertIsNone(issue)


# -- check_physics_material: needs Material.isPhysicsMaterial registered -----

class TestPhysicsMaterialCheck(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _addon.pyshics_materials.register()

    @classmethod
    def tearDownClass(cls):
        _addon.pyshics_materials.unregister()

    def tearDown(self):
        _remove_test_objects()
        _remove_test_materials()

    def test_physics_material_pass(self):
        obj = _make_cube_object(_TEST_PREFIX + 'cube')
        mat = bpy.data.materials.new(_TEST_PREFIX + 'mat')
        mat.isPhysicsMaterial = True
        obj.data.materials.append(mat)
        issue = _checks.check_physics_material(obj)
        self.assertIsNone(issue)

    def test_physics_material_flagged_no_material(self):
        obj = _make_cube_object(_TEST_PREFIX + 'cube')
        issue = _checks.check_physics_material(obj)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'physics_material')

    def test_physics_material_flagged_wrong_tag(self):
        obj = _make_cube_object(_TEST_PREFIX + 'cube')
        mat = bpy.data.materials.new(_TEST_PREFIX + 'mat')
        mat.isPhysicsMaterial = False
        obj.data.materials.append(mat)
        issue = _checks.check_physics_material(obj)
        self.assertIsNotNone(issue)


# -- Preferences-dependent checks ---------------------------------------------

def _add_parent(name):
    """Create a non-collider parent (render mesh) object."""
    return _make_cube_object(name)


def _add_collider(name, parent=None, shape='box_shape', use_parent_to=True):
    obj = _make_cube_object(name)
    obj['isCollider'] = True
    if shape is not None:
        obj['collider_shape'] = shape
    if parent is not None and use_parent_to:
        obj.parent = parent
    return obj


class TestPrefsDependentChecks(unittest.TestCase):
    """check_missing_collider, check_naming_convention and
    check_parent_hierarchy read addon naming/parenting preferences."""

    @classmethod
    def setUpClass(cls):
        bpy.utils.register_class(_CollisionAddonPrefs)
        bpy.context.preferences.addons.new().module = _ADDON_NAME

    @classmethod
    def tearDownClass(cls):
        addons = bpy.context.preferences.addons
        entry = addons.get(_ADDON_NAME)
        if entry is not None:
            addons.remove(entry)
        bpy.utils.unregister_class(_CollisionAddonPrefs)

    def setUp(self):
        _remove_test_objects()
        self.prefs = bpy.context.preferences.addons[_ADDON_NAME].preferences
        if self.prefs.separator != '_':
            self.skipTest("test assumes separator='_'")
        if self.prefs.box_shape != 'UBX':
            self.skipTest("test assumes box_shape='UBX'")
        if self.prefs.mesh_shape != '':
            self.skipTest("test assumes mesh_shape=''")
        if not self.prefs.use_parent_to:
            self.skipTest("test assumes use_parent_to=True by default")

    def tearDown(self):
        _remove_test_objects()

    # -- missing_collider ------------------------------------------------

    def test_missing_collider_flagged(self):
        render_obj = _add_parent(_TEST_PREFIX + 'render')
        issue = _checks.check_missing_collider(render_obj, use_parent_to=True)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'missing_collider')

    def test_missing_collider_pass_when_child_exists(self):
        render_obj = _add_parent(_TEST_PREFIX + 'render')
        _add_collider(_TEST_PREFIX + 'UBX_render_001', parent=render_obj)
        issue = _checks.check_missing_collider(render_obj, use_parent_to=True)
        self.assertIsNone(issue)

    def test_missing_collider_skipped_when_parenting_disabled(self):
        render_obj = _add_parent(_TEST_PREFIX + 'render')
        issue = _checks.check_missing_collider(render_obj, use_parent_to=False)
        self.assertIsNone(issue)

    # -- naming_convention -------------------------------------------------

    def test_naming_convention_pass(self):
        collider = _add_collider(_TEST_PREFIX + 'UBX_Thing_001', shape='box_shape')
        issue = _checks.check_naming_convention(collider, self.prefs)
        self.assertIsNone(issue)

    def test_naming_convention_flagged(self):
        collider = _add_collider(_TEST_PREFIX + 'WrongName', shape='box_shape')
        issue = _checks.check_naming_convention(collider, self.prefs)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'naming')

    def test_naming_convention_skipped_when_shape_string_empty(self):
        # Default mesh_shape == '' -> nothing configured to enforce.
        collider = _add_collider(_TEST_PREFIX + 'AnyName', shape='mesh_shape')
        issue = _checks.check_naming_convention(collider, self.prefs)
        self.assertIsNone(issue)

    def test_naming_convention_skipped_when_shape_unset(self):
        collider = _add_collider(_TEST_PREFIX + 'AnyName', shape=None)
        issue = _checks.check_naming_convention(collider, self.prefs)
        self.assertIsNone(issue)

    # -- parent_hierarchy ---------------------------------------------------

    def test_parent_hierarchy_flagged_no_parent(self):
        collider = _add_collider(_TEST_PREFIX + 'UBX_Thing_001')
        issue = _checks.check_parent_hierarchy(collider, use_parent_to=True)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'parent_hierarchy')

    def test_parent_hierarchy_pass_with_render_mesh_parent(self):
        render_obj = _add_parent(_TEST_PREFIX + 'render')
        collider = _add_collider(_TEST_PREFIX + 'UBX_render_001', parent=render_obj)
        issue = _checks.check_parent_hierarchy(collider, use_parent_to=True)
        self.assertIsNone(issue)

    def test_parent_hierarchy_flagged_parent_is_collider(self):
        other_collider = _add_collider(_TEST_PREFIX + 'UBX_Other_001')
        collider = _add_collider(_TEST_PREFIX + 'UBX_Thing_001', parent=other_collider)
        issue = _checks.check_parent_hierarchy(collider, use_parent_to=True)
        self.assertIsNotNone(issue)

    def test_parent_hierarchy_skipped_when_parenting_disabled(self):
        collider = _add_collider(_TEST_PREFIX + 'UBX_Thing_001')
        issue = _checks.check_parent_hierarchy(collider, use_parent_to=False)
        self.assertIsNone(issue)

    def test_parent_hierarchy_flagged_invalid_parent_type(self):
        # An EMPTY isn't in VALID_OBJECT_TYPES ({'MESH','CURVE','SURFACE',
        # 'FONT','META'}), so parenting a collider to one should be flagged
        # even though it's neither "no parent" nor "parent is a collider".
        empty_parent = bpy.data.objects.new(_TEST_PREFIX + 'empty_parent', None)
        bpy.context.collection.objects.link(empty_parent)
        collider = _add_collider(_TEST_PREFIX + 'UBX_Thing_001', parent=empty_parent)
        issue = _checks.check_parent_hierarchy(collider, use_parent_to=True)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'parent_hierarchy')

    # -- parent_inverse_matrix -----------------------------------------------

    def test_parent_inverse_matrix_pass_no_parent(self):
        collider = _add_collider(_TEST_PREFIX + 'UBX_Thing_001')
        issue = _checks.check_parent_inverse_matrix(collider)
        self.assertIsNone(issue)

    def test_parent_inverse_matrix_pass_when_identity(self):
        # obj.parent = parent (as _add_collider does) leaves
        # matrix_parent_inverse at its default identity value.
        render_obj = _add_parent(_TEST_PREFIX + 'render')
        collider = _add_collider(_TEST_PREFIX + 'UBX_render_001', parent=render_obj)
        self.assertTrue(collider.matrix_parent_inverse.is_identity)
        issue = _checks.check_parent_inverse_matrix(collider)
        self.assertIsNone(issue)

    def test_parent_inverse_matrix_flagged_when_not_identity(self):
        render_obj = _add_parent(_TEST_PREFIX + 'render')
        render_obj.rotation_euler = (0.3, 0.1, 0.0)
        bpy.context.view_layer.update()
        collider = _add_collider(_TEST_PREFIX + 'UBX_render_001', parent=render_obj)
        collider.matrix_parent_inverse = render_obj.matrix_world.inverted()
        issue = _checks.check_parent_inverse_matrix(collider)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'parent_inverse_matrix')
        self.assertEqual(issue.severity, 'WARNING')


# -- check_naming_convention: user-controlled regex safety -------------------

class TestNamingConventionRegexSafety(unittest.TestCase):
    """check_naming_convention builds a regex out of free-text, user-editable
    preference strings (separator, box_shape, etc. - preferences/
    prefs_properties.py has no character restriction on them). Before checks.
    py escaped them with re.escape(), a separator/shape string containing a
    regex metacharacter either silently weakened the match (e.g. '.' acting
    as "any character") or raised re.error - uncaught anywhere up the call
    chain, which would crash the whole "Validate Colliders" popup."""

    def tearDown(self):
        _remove_test_objects()

    def test_metacharacter_separator_matches_literally_and_does_not_raise(self):
        prefs = SimpleNamespace(separator='.', box_shape='UBX')
        collider = _make_cube_object(_TEST_PREFIX + 'Thing.UBX')
        collider['collider_shape'] = 'box_shape'
        issue = _checks.check_naming_convention(collider, prefs)
        self.assertIsNone(issue)

    def test_metacharacter_separator_is_not_treated_as_wildcard(self):
        # If '.' were left as a live regex wildcard instead of a literal
        # character, 'X' here would wrongly satisfy "any character" and this
        # would incorrectly pass. It must be flagged.
        prefs = SimpleNamespace(separator='.', box_shape='UBX')
        collider = _make_cube_object(_TEST_PREFIX + 'ThingXUBXY')
        collider['collider_shape'] = 'box_shape'
        issue = _checks.check_naming_convention(collider, prefs)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'naming')

    def test_unbalanced_bracket_in_shape_string_does_not_raise(self):
        # 'UB[X' is invalid regex syntax (unterminated character set) if used
        # unescaped - re.compile would raise re.error here before the fix.
        prefs = SimpleNamespace(separator='_', box_shape='UB[X')
        collider = _make_cube_object(_TEST_PREFIX + 'Thing_UB[X_001')
        collider['collider_shape'] = 'box_shape'
        issue = _checks.check_naming_convention(collider, prefs)
        self.assertIsNone(issue)


# -- collect_validation_issues: the top-level aggregator ---------------------

class TestCollectValidationIssues(unittest.TestCase):
    """collect_validation_issues() is invoked directly by
    COLLISION_OT_validate_colliders and is responsible for (a) gating each
    check on its prefs.validate_check_* toggle, (b) routing collider vs.
    non-collider / MESH vs. non-MESH objects to the right checks, and (c)
    isolating a failure on one object so it doesn't hide every other
    object's results. None of that was previously covered - only the
    individual check_* functions were tested in isolation."""

    def tearDown(self):
        _remove_test_objects()

    def test_disabled_checks_produce_no_issues(self):
        prefs = _make_fake_prefs()  # every validate_check_* off
        render_obj = _make_cube_object(_TEST_PREFIX + 'render')
        collider = _make_cube_object(_TEST_PREFIX + 'collider')
        collider['isCollider'] = True
        collider.parent = render_obj
        issues = _checks.collect_validation_issues([render_obj, collider], prefs, _depsgraph())
        self.assertEqual(issues, [])

    def test_only_the_enabled_check_dispatches(self):
        prefs = _make_fake_prefs(validate_check_missing_collider=True)
        render_obj = _make_cube_object(_TEST_PREFIX + 'render')  # no collider children
        issues = _checks.collect_validation_issues([render_obj], prefs, _depsgraph())
        self.assertEqual([i.check_id for i in issues], ['missing_collider'])

    def test_non_mesh_render_parent_is_scanned(self):
        """Regression test: collect_validation_issues() used to gate
        missing_collider/bbox_mismatch/too_many_colliders on
        obj.type == 'MESH', silently skipping CURVE/SURFACE/FONT/META render
        objects even though VALID_OBJECT_TYPES (used elsewhere in the same
        module, e.g. check_parent_hierarchy) treats them as valid render
        meshes."""
        prefs = _make_fake_prefs(validate_check_missing_collider=True)
        bpy.ops.curve.primitive_bezier_curve_add()
        curve_obj = bpy.context.active_object
        curve_obj.name = _TEST_PREFIX + 'curve_render'
        self.assertEqual(curve_obj.type, 'CURVE')
        issues = _checks.collect_validation_issues([curve_obj], prefs, _depsgraph())
        self.assertEqual([i.check_id for i in issues], ['missing_collider'])

    def test_isCollider_non_mesh_object_gets_naming_and_parent_checks(self):
        # check_naming_convention/check_parent_hierarchy aren't gated on
        # obj.type == 'MESH' - an EMPTY tagged isCollider must still be
        # scanned by both.
        prefs = _make_fake_prefs(validate_check_naming=True, validate_check_parent_hierarchy=True)
        empty = bpy.data.objects.new(_TEST_PREFIX + 'WrongName', None)
        bpy.context.collection.objects.link(empty)
        empty['isCollider'] = True
        empty['collider_shape'] = 'box_shape'
        issues = _checks.collect_validation_issues([empty], prefs, _depsgraph())
        self.assertEqual(sorted(i.check_id for i in issues), ['naming', 'parent_hierarchy'])

    def test_one_bad_object_does_not_abort_the_whole_scan(self):
        prefs = _make_fake_prefs(validate_check_physics_material=True)
        good = _make_cube_object(_TEST_PREFIX + 'good')
        good['isCollider'] = True
        bad = _make_cube_object(_TEST_PREFIX + 'bad')
        bad['isCollider'] = True

        original = _checks.check_physics_material

        def _boom(obj):
            if obj is bad:
                raise RuntimeError('boom')
            return original(obj)

        _checks.check_physics_material = _boom
        try:
            issues = _checks.collect_validation_issues([good, bad], prefs, _depsgraph())
        finally:
            _checks.check_physics_material = original

        by_object = {issue.object_name: issue for issue in issues}
        self.assertEqual(by_object[good.name].check_id, 'physics_material')
        self.assertEqual(by_object[bad.name].check_id, 'internal_error')
        self.assertEqual(by_object[bad.name].severity, 'ERROR')

    def test_progress_callback_invoked_once_per_object(self):
        prefs = _make_fake_prefs()
        objs = [_make_cube_object(_TEST_PREFIX + f'o{i}') for i in range(3)]
        calls = []
        _checks.collect_validation_issues(
            objs, prefs, _depsgraph(),
            progress_callback=lambda done, total: calls.append((done, total)),
        )
        self.assertEqual(calls, [(1, 3), (2, 3), (3, 3)])


# -- Evaluated (post-modifier) vs. local mesh usage --------------------------

class TestEvaluatedMeshUsage(unittest.TestCase):
    """check_triangle_count/check_non_manifold/check_flipped_normals read
    the evaluated (post-modifier) mesh via depsgraph; check_min_dimension
    intentionally reads the local, pre-modifier mesh instead (see its
    docstring). Neither path had modifier-stack coverage before."""

    def tearDown(self):
        _remove_test_objects()

    def _evaluated_depsgraph(self):
        bpy.context.view_layer.update()
        return bpy.context.evaluated_depsgraph_get()

    def test_triangle_count_reflects_mirror_modifier(self):
        # A closed cube alone is 12 tris; Mirror doubles it to 24 in the
        # evaluated mesh without changing the 8-vert/12-tri base mesh.
        obj = _make_cube_object(_TEST_PREFIX + 'cube')
        obj['collider_shape'] = 'mesh_shape'
        obj.modifiers.new(name='Mirror', type='MIRROR')
        depsgraph = self._evaluated_depsgraph()
        issue = _checks.check_triangle_count(obj, max_triangles=12, depsgraph=depsgraph)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'triangle_count')

    def test_non_manifold_reflects_modifier_result(self):
        # A 5-face open cube is non-manifold on its own; Solidify seals the
        # open rim into a closed shell purely via the modifier stack.
        obj = _make_cube_object(_TEST_PREFIX + 'cube', face_count=5)
        obj.modifiers.new(name='Solidify', type='SOLIDIFY')
        depsgraph = self._evaluated_depsgraph()
        issue = _checks.check_non_manifold(obj, depsgraph=depsgraph)
        self.assertIsNone(issue)

    def test_min_dimension_ignores_modifier_result(self):
        # Local extent is 0.8 (below the 1.0 threshold); Mirror roughly
        # doubles the evaluated extent, but must NOT change this check's
        # verdict since it intentionally reads the local mesh.
        obj = _make_cube_object(_TEST_PREFIX + 'cube', half_extent=0.4)
        obj.modifiers.new(name='Mirror', type='MIRROR')
        issue = _checks.check_min_dimension(obj, min_dimension=1.0)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'min_dimension')


if __name__ == '__main__':
    # Strip Blender's argv; everything after '--' is forwarded to unittest.
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
