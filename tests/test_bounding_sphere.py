"""Unit tests for calculate_bounding_sphere().

Run with headless Blender::

    blender --background --python tests/test_bounding_sphere.py
"""
import math
import os
import sys
import unittest

import bpy
from mathutils import Matrix, Vector

# Make the add-on importable as a package.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ADDON_NAME = os.path.basename(_PROJECT_ROOT)
sys.path.insert(0, os.path.dirname(_PROJECT_ROOT))

_addon = __import__(_ADDON_NAME)
_sphere_mod = _addon.collider_shapes.add_bounding_sphere

calculate_bounding_sphere = (
    _sphere_mod.OBJECT_OT_add_bounding_sphere.calculate_bounding_sphere
)

# -- Helpers -----------------------------------------------------------------


def _make_obj(vertices, matrix_world=None):
    """Create a Blender object whose mesh contains *vertices*.

    Returns the object. Caller is responsible for cleanup via ``_remove_obj``.
    """
    mesh = bpy.data.meshes.new('test_mesh')
    mesh.vertices.add(len(vertices))
    for i, co in enumerate(vertices):
        mesh.vertices[i].co = co
    obj = bpy.data.objects.new('test_obj', mesh)
    bpy.context.collection.objects.link(obj)
    if matrix_world is not None:
        obj.matrix_world = matrix_world
    return obj


def _remove_obj(obj):
    """Delete a Blender object and its mesh data."""
    mesh = obj.data
    bpy.data.objects.remove(obj)
    bpy.data.meshes.remove(mesh)


def _assert_encloses(test_case, center, radius, points, tol=1e-6):
    """Assert that every point lies within *radius* of *center*."""
    for p in points:
        d = (p - center).length
        test_case.assertLessEqual(
            d, radius + tol,
            f"Point {p} at distance {d:.6f} is outside sphere "
            f"(center={center}, radius={radius:.6f})",
        )


def _assert_sphere(test_case, center, radius, points,
                    expected_center, expected_radius, places=5):
    """Assert enclosure *and* that center/radius match the known optimum."""
    _assert_encloses(test_case, center, radius,
                     [Vector(p) for p in points])
    test_case.assertAlmostEqual(
        center.x, expected_center[0], places=places,
        msg=f"center.x: {center.x} != {expected_center[0]}",
    )
    test_case.assertAlmostEqual(
        center.y, expected_center[1], places=places,
        msg=f"center.y: {center.y} != {expected_center[1]}",
    )
    test_case.assertAlmostEqual(
        center.z, expected_center[2], places=places,
        msg=f"center.z: {center.z} != {expected_center[2]}",
    )
    test_case.assertAlmostEqual(
        radius, expected_radius, places=places,
        msg=f"radius: {radius} != {expected_radius}",
    )


# -- Tests -------------------------------------------------------------------

class TestBoundingSphere(unittest.TestCase):
    """Tests for calculate_bounding_sphere with an identity world matrix.

    Each test asserts that the result is the *minimum enclosing sphere*
    (center and radius match the analytically known optimum).
    """

    def setUp(self):
        self._objs = []

    def tearDown(self):
        for obj in self._objs:
            _remove_obj(obj)

    def _obj(self, pts, matrix_world=None):
        """Create a test object from coordinate tuples and track it."""
        obj = _make_obj(pts, matrix_world)
        self._objs.append(obj)
        return obj

    # -- 1. Single point -----------------------------------------------------

    def test_single_point(self):
        pts = [(3, 5, 7)]
        obj = self._obj(pts)
        center, radius = calculate_bounding_sphere(obj, obj.data.vertices)
        _assert_sphere(self, center, radius, pts,
                       expected_center=(3, 5, 7), expected_radius=0.0)

    # -- 2. Two points -------------------------------------------------------

    def test_two_points(self):
        pts = [(1, 0, 0), (5, 0, 0)]
        obj = self._obj(pts)
        center, radius = calculate_bounding_sphere(obj, obj.data.vertices)
        _assert_sphere(self, center, radius, pts,
                       expected_center=(3, 0, 0), expected_radius=2.0)

    def test_two_points_diagonal(self):
        pts = [(0, 0, 0), (2, 2, 2)]
        obj = self._obj(pts)
        center, radius = calculate_bounding_sphere(obj, obj.data.vertices)
        _assert_sphere(self, center, radius, pts,
                       expected_center=(1, 1, 1),
                       expected_radius=math.sqrt(3))

    # -- 3. Three collinear points -------------------------------------------

    def test_three_collinear(self):
        pts = [(0, 0, 0), (1, 0, 0), (3, 0, 0)]
        obj = self._obj(pts)
        center, radius = calculate_bounding_sphere(obj, obj.data.vertices)
        _assert_sphere(self, center, radius, pts,
                       expected_center=(1.5, 0, 0), expected_radius=1.5)

    # -- 4. Three non-collinear points ---------------------------------------

    def test_three_non_collinear(self):
        """Right triangle – the hypotenuse is the diameter of the minimum
        enclosing sphere."""
        pts = [(0, 0, 0), (2, 0, 0), (0, 2, 0)]
        obj = self._obj(pts)
        center, radius = calculate_bounding_sphere(obj, obj.data.vertices)
        _assert_sphere(self, center, radius, pts,
                       expected_center=(1, 1, 0),
                       expected_radius=math.sqrt(2))

    def test_three_non_collinear_equilateral(self):
        """Equilateral triangle – circumradius equals the vertex distance."""
        pts = [
            (1, 0, 0),
            (-0.5, math.sqrt(3) / 2, 0),
            (-0.5, -math.sqrt(3) / 2, 0),
        ]
        obj = self._obj(pts)
        center, radius = calculate_bounding_sphere(obj, obj.data.vertices)
        _assert_sphere(self, center, radius, pts,
                       expected_center=(0, 0, 0), expected_radius=1.0)

    # -- 5. Four coplanar points ---------------------------------------------

    def test_four_coplanar_square(self):
        pts = [(1, 1, 0), (-1, 1, 0), (-1, -1, 0), (1, -1, 0)]
        obj = self._obj(pts)
        center, radius = calculate_bounding_sphere(obj, obj.data.vertices)
        _assert_sphere(self, center, radius, pts,
                       expected_center=(0, 0, 0),
                       expected_radius=math.sqrt(2))

    def test_four_coplanar_rectangle(self):
        pts = [(3, 1, 0), (-3, 1, 0), (-3, -1, 0), (3, -1, 0)]
        obj = self._obj(pts)
        center, radius = calculate_bounding_sphere(obj, obj.data.vertices)
        _assert_sphere(self, center, radius, pts,
                       expected_center=(0, 0, 0),
                       expected_radius=math.sqrt(10))

    # -- 6. Four non-coplanar points (tetrahedron) ---------------------------

    def test_four_non_coplanar_regular_tetrahedron(self):
        """Regular tetrahedron inscribed in a sphere of radius sqrt(3)."""
        pts = [
            (1, 1, 1),
            (1, -1, -1),
            (-1, 1, -1),
            (-1, -1, 1),
        ]
        obj = self._obj(pts)
        center, radius = calculate_bounding_sphere(obj, obj.data.vertices)
        _assert_sphere(self, center, radius, pts,
                       expected_center=(0, 0, 0),
                       expected_radius=math.sqrt(3))

    def test_four_non_coplanar_asymmetric(self):
        """Asymmetric tetrahedron whose circumcenter lies outside the
        tetrahedron. The minimum enclosing sphere is defined by the three
        non-origin vertices; (0,0,0) is inside the sphere."""
        pts = [(0, 0, 0), (4, 0, 0), (0, 3, 0), (0, 0, 5)]
        obj = self._obj(pts)
        center, radius = calculate_bounding_sphere(obj, obj.data.vertices)
        # Exact: center = (1088/769, 1107/1538, 3125/1538),
        #        radius = sqrt(17425/1538)
        _assert_sphere(self, center, radius, pts,
                       expected_center=(1088 / 769, 1107 / 1538, 3125 / 1538),
                       expected_radius=math.sqrt(17425 / 1538))

    # -- 7. Eight points – unit cube -----------------------------------------

    def test_cube(self):
        """Unit cube centred at the origin – minimum enclosing radius is
        sqrt(3)."""
        pts = [
            (-1, -1, -1),
            (-1, -1,  1),
            (-1,  1, -1),
            (-1,  1,  1),
            ( 1, -1, -1),
            ( 1, -1,  1),
            ( 1,  1, -1),
            ( 1,  1,  1),
        ]
        obj = self._obj(pts)
        center, radius = calculate_bounding_sphere(obj, obj.data.vertices)
        _assert_sphere(self, center, radius, pts,
                       expected_center=(0, 0, 0),
                       expected_radius=math.sqrt(3))

    def test_cube_offset(self):
        """Cube not centred at the origin."""
        pts = [
            ( 9, -6, 2),
            ( 9, -6, 4),
            ( 9, -4, 2),
            ( 9, -4, 4),
            (11, -6, 2),
            (11, -6, 4),
            (11, -4, 2),
            (11, -4, 4),
        ]
        obj = self._obj(pts)
        center, radius = calculate_bounding_sphere(obj, obj.data.vertices)
        _assert_sphere(self, center, radius, pts,
                       expected_center=(10, -5, 3),
                       expected_radius=math.sqrt(3))

    # -- 8. Large point set (exceeds default recursion limit) ----------------

    def test_large_point_set(self):
        """High-subdivision icosphere with >1000 vertices does not cause
        RecursionError."""
        src_radius = 5.0
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=5, radius=src_radius)
        obj = bpy.context.active_object
        self._objs.append(obj)
        self.assertGreater(len(obj.data.vertices), 1000)

        old_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(500)
        try:
            center, radius = calculate_bounding_sphere(obj, obj.data.vertices)
        finally:
            sys.setrecursionlimit(old_limit)

        pts = [tuple(obj.matrix_world @ v.co) for v in obj.data.vertices]
        _assert_sphere(self, center, radius, pts,
                       expected_center=(0, 0, 0),
                       expected_radius=src_radius, places=4)

    # -- 9. Icosphere (42 uniformly distributed vertices) --------------------

    def test_icosphere(self):
        """Icosphere (2 subdivisions, radius 5) at the origin."""
        src_radius = 5.0
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=2, radius=src_radius)
        obj = bpy.context.active_object
        self._objs.append(obj)
        center, radius = calculate_bounding_sphere(obj, obj.data.vertices)

        pts = [tuple(obj.matrix_world @ v.co) for v in obj.data.vertices]
        _assert_sphere(self, center, radius, pts,
                       expected_center=(0, 0, 0),
                       expected_radius=src_radius, places=4)

    def test_icosphere_offset(self):
        """Icosphere (2 subdivisions, radius 3) away from the origin."""
        src_radius = 3.0
        tx, ty, tz = 7, -4, 2
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=2, radius=src_radius)
        obj = bpy.context.active_object
        obj.matrix_world = Matrix.Translation(Vector((tx, ty, tz)))
        self._objs.append(obj)
        center, radius = calculate_bounding_sphere(obj, obj.data.vertices)

        pts = [tuple(obj.matrix_world @ v.co) for v in obj.data.vertices]
        _assert_sphere(self, center, radius, pts,
                       expected_center=(tx, ty, tz),
                       expected_radius=src_radius, places=4)


if __name__ == '__main__':
    # Strip Blender's argv; everything after '--' is forwarded to unittest.
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
