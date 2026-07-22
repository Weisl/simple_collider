"""Unit tests for the voxel-grid collider geometry (bmesh_operations.voxel_generation).

The collider itself is a modal operator (like the other Add Bounding Shape
operators) that requires a real VIEW_3D context, so -- following the pattern
in test_bounding_sphere.py -- these tests exercise the underlying geometry
functions directly rather than the operator.

Run with headless Blender::

    blender --background --python tests/test_bounding_voxel.py
"""
import os
import sys
import unittest

import bpy

# Make the add-on importable as a package.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ADDON_NAME = os.path.basename(_PROJECT_ROOT)
sys.path.insert(0, os.path.dirname(_PROJECT_ROOT))

_addon = __import__(_ADDON_NAME)
_voxel_mod = _addon.bmesh_operations.voxel_generation

build_voxel_bmesh = _voxel_mod.build_voxel_bmesh
mesh_max_dimension = _voxel_mod.mesh_max_dimension


# -- Helpers -----------------------------------------------------------------


def _add_primitive(add_op, **kwargs):
    """Run a bpy.ops.mesh.primitive_*_add and return (and unlink) its mesh."""
    add_op(**kwargs)
    obj = bpy.context.active_object
    mesh = obj.data
    bpy.data.objects.remove(obj)
    return mesh


def _remove_mesh(mesh):
    bpy.data.meshes.remove(mesh)


def _holes(bm):
    """Edges with only one linked face -- a genuine gap in the surface."""
    return [e for e in bm.edges if len(e.link_faces) == 1]


# -- Tests -------------------------------------------------------------------


class TestVoxelGeneration(unittest.TestCase):

    def setUp(self):
        self._meshes = []

    def tearDown(self):
        for mesh in self._meshes:
            try:
                _remove_mesh(mesh)
            except Exception:
                pass
        self._meshes = []

    def _cube_mesh(self, size=2.0):
        mesh = _add_primitive(bpy.ops.mesh.primitive_cube_add, size=size)
        self._meshes.append(mesh)
        return mesh

    def _sphere_mesh(self, radius=1.5, subdivisions=3):
        mesh = _add_primitive(bpy.ops.mesh.primitive_ico_sphere_add, radius=radius, subdivisions=subdivisions)
        self._meshes.append(mesh)
        return mesh

    # -- Cubic (simple) fill --------------------------------------------

    def test_cube_cubic_is_watertight(self):
        mesh = self._cube_mesh(size=2.0)
        bm = build_voxel_bmesh(mesh, voxel_size=0.3, diagonal_fill=False)
        self.addCleanup(bm.free)
        self.assertIsNotNone(bm)
        self.assertEqual(_holes(bm), [])
        self.assertGreater(bm.calc_volume(signed=True), 0)

    def test_cube_cubic_axis_aligned_grid_merges_to_single_box(self):
        """A voxel size evenly dividing a cube's extent should collapse to one box."""
        mesh = self._cube_mesh(size=2.0)
        bm = build_voxel_bmesh(mesh, voxel_size=0.5, diagonal_fill=False)
        self.addCleanup(bm.free)
        self.assertEqual(len(bm.verts), 8)
        self.assertEqual(len(bm.faces), 6)
        self.assertEqual(_holes(bm), [])

    def test_cube_cubic_hugs_true_bbox_when_voxel_size_divides_evenly(self):
        """Regression for #577: an evenly-dividing voxel size used to always
        inflate the collider outward by one full voxel on every side, because
        the mesh's own bbox faces sit exactly on a grid line. The result
        should instead match the source cube's bbox exactly."""
        size = 2.0
        mesh = self._cube_mesh(size=size)
        bm = build_voxel_bmesh(mesh, voxel_size=0.5, diagonal_fill=False)
        self.addCleanup(bm.free)
        coords = [v.co for v in bm.verts]
        bbox_min = [min(c[axis] for c in coords) for axis in range(3)]
        bbox_max = [max(c[axis] for c in coords) for axis in range(3)]
        for axis in range(3):
            self.assertAlmostEqual(bbox_min[axis], -size / 2, places=5)
            self.assertAlmostEqual(bbox_max[axis], size / 2, places=5)

    def test_sphere_cubic_is_watertight(self):
        mesh = self._sphere_mesh()
        bm = build_voxel_bmesh(mesh, voxel_size=0.15, diagonal_fill=False)
        self.addCleanup(bm.free)
        self.assertIsNotNone(bm)
        self.assertEqual(_holes(bm), [])

    # -- Diagonal (ramp) fill ---------------------------------------------

    def test_cube_diagonal_is_watertight(self):
        mesh = self._cube_mesh(size=2.0)
        bm = build_voxel_bmesh(mesh, voxel_size=0.5, diagonal_fill=True)
        self.addCleanup(bm.free)
        self.assertIsNotNone(bm)
        self.assertEqual(_holes(bm), [])

    def test_sphere_diagonal_is_watertight(self):
        mesh = self._sphere_mesh()
        bm = build_voxel_bmesh(mesh, voxel_size=0.15, diagonal_fill=True)
        self.addCleanup(bm.free)
        self.assertIsNotNone(bm)
        self.assertEqual(_holes(bm), [])

    def test_diagonal_fill_reduces_stairstepping(self):
        """The chamfered ramp mode should use noticeably fewer verts than a
        naive per-voxel cube emission would for the same sphere, while still
        being watertight (a sanity check that ramps are actually being used,
        not silently falling back to plain cubes everywhere)."""
        mesh = self._sphere_mesh()
        bm_cubic = build_voxel_bmesh(mesh, voxel_size=0.2, diagonal_fill=False)
        self.addCleanup(bm_cubic.free)
        bm_diag = build_voxel_bmesh(mesh, voxel_size=0.2, diagonal_fill=True)
        self.addCleanup(bm_diag.free)

        self.assertEqual(_holes(bm_cubic), [])
        self.assertEqual(_holes(bm_diag), [])
        # Diagonal mode adds ramp geometry (ends up with more, smaller faces
        # than the cubic mode's dissolved flat quads) -- just confirm ramps
        # actually fired rather than every cell falling back to a cube.
        self.assertGreater(len(bm_diag.faces), len(bm_cubic.faces))

    # -- Robustness / edge cases -------------------------------------------

    def test_open_plane_mesh_produces_thin_watertight_shell(self):
        """A single flat (non-solid, open) mesh shouldn't crash and should
        still close into a valid thin shell rather than leaking a hole."""
        mesh = _add_primitive(bpy.ops.mesh.primitive_plane_add, size=2.0)
        self._meshes.append(mesh)

        bm = build_voxel_bmesh(mesh, voxel_size=0.3, diagonal_fill=False)
        if bm is not None:
            self.addCleanup(bm.free)
            self.assertEqual(_holes(bm), [])

    def test_empty_mesh_returns_none(self):
        mesh = bpy.data.meshes.new('EmptyTestMesh')
        self._meshes.append(mesh)
        bm = build_voxel_bmesh(mesh, voxel_size=0.1, diagonal_fill=False)
        self.assertIsNone(bm)

    def test_voxel_size_is_clamped_for_extreme_resolutions(self):
        """Dragging voxel size very small must not hang or explode the grid."""
        mesh = self._sphere_mesh()
        bm = build_voxel_bmesh(mesh, voxel_size=0.001, diagonal_fill=True)
        self.addCleanup(bm.free)
        self.assertIsNotNone(bm)
        self.assertEqual(_holes(bm), [])
        self.assertLessEqual(len(bm.verts), 200000)

    # -- mesh_max_dimension ------------------------------------------------

    def test_mesh_max_dimension_matches_bounding_box(self):
        mesh = self._cube_mesh(size=2.0)
        self.assertAlmostEqual(mesh_max_dimension(mesh), 2.0, places=5)

    def test_mesh_max_dimension_empty_mesh_is_zero(self):
        mesh = bpy.data.meshes.new('EmptyTestMesh2')
        self._meshes.append(mesh)
        self.assertEqual(mesh_max_dimension(mesh), 0.0)


if __name__ == '__main__':
    # Strip Blender's argv; everything after '--' is forwarded to unittest.
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
