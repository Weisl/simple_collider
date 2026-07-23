"""Unit tests for the collider validation checks (validation/checks.py).

Run with headless Blender::

    blender --background --python tests/test_validation_checks.py
"""
import os
import sys
import unittest

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
        issue = _checks.check_triangle_count(obj, max_triangles=12, depsgraph=_depsgraph())
        self.assertIsNone(issue)

    def test_triangle_count_flagged(self):
        obj = _make_cube_object(_TEST_PREFIX + 'cube')
        issue = _checks.check_triangle_count(obj, max_triangles=5, depsgraph=_depsgraph())
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'triangle_count')
        self.assertEqual(issue.object_name, obj.name)

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
        issue = _checks.check_bbox_mismatch(collider_obj, render_obj, tolerance=0.1, depsgraph=_depsgraph())
        self.assertIsNone(issue)

    def test_bbox_mismatch_flagged_when_offset(self):
        render_obj = _make_cube_object(_TEST_PREFIX + 'render', half_extent=1.0)
        collider_obj = _make_cube_object(
            _TEST_PREFIX + 'collider', half_extent=1.0,
            matrix_world=Matrix.Translation((1.0, 0.0, 0.0)),
        )
        issue = _checks.check_bbox_mismatch(collider_obj, render_obj, tolerance=0.1, depsgraph=_depsgraph())
        self.assertIsNotNone(issue)
        self.assertEqual(issue.check_id, 'bbox_mismatch')

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


if __name__ == '__main__':
    # Strip Blender's argv; everything after '--' is forwarded to unittest.
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
