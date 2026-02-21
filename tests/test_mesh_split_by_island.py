"""Unit tests for bmesh_operations/mesh_split_by_island.py.

Run with headless Blender::

    blender --background --python tests/test_mesh_split_by_island.py
"""
import os
import statistics
import sys
import time
import unittest

import bmesh

# Make the add-on importable as a package.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ADDON_NAME = os.path.basename(_PROJECT_ROOT)
sys.path.insert(0, os.path.dirname(_PROJECT_ROOT))

_addon = __import__(_ADDON_NAME)
_island_mod = _addon.bmesh_operations.mesh_split_by_island

_get_face_islands = _island_mod.get_face_islands


# -- Helpers -----------------------------------------------------------------


def _make_connected_grid(n_rows, n_cols):
    """Create a bmesh with an n_rows x n_cols grid of quads (one connected island)."""
    bm = bmesh.new()
    verts = [[bm.verts.new((float(x), float(y), 0.0))
              for x in range(n_cols + 1)]
             for y in range(n_rows + 1)]
    for y in range(n_rows):
        for x in range(n_cols):
            bm.faces.new([verts[y][x], verts[y][x + 1],
                          verts[y + 1][x + 1], verts[y + 1][x]])
    return bm


def _make_bm_with_islands(n_islands):
    """Create a bmesh with *n_islands* completely disconnected triangles."""
    bm = bmesh.new()
    for i in range(n_islands):
        x = float(i) * 2.0
        v1 = bm.verts.new((x, 0.0, 0.0))
        v2 = bm.verts.new((x + 1.0, 0.0, 0.0))
        v3 = bm.verts.new((x, 1.0, 0.0))
        bm.faces.new([v1, v2, v3])
    return bm


class TestGetFaceIslands(unittest.TestCase):

    def setUp(self):
        self.bm = None

    def tearDown(self):
        if self.bm is not None:
            self.bm.free()
            self.bm = None

    # -- 1. Single island ----------------------------------------------------

    def test_single_island(self):
        """A single triangle produces exactly one island."""
        self.bm = _make_bm_with_islands(1)

        islands = _get_face_islands(self.bm, list(self.bm.faces), [])

        self.assertEqual(len(islands), 1)
        self.assertEqual(len(islands[0]['py_faces']), 1)
        self.assertEqual(len(islands[0]['py_verts']), 3)

    # -- 2. Two disconnected islands -----------------------------------------

    def test_two_islands(self):
        """Two disconnected triangles produce exactly two islands."""
        self.bm = _make_bm_with_islands(2)

        islands = _get_face_islands(self.bm, list(self.bm.faces), [])

        self.assertEqual(len(islands), 2)
        for island in islands:
            self.assertEqual(len(island['py_faces']), 1)
            self.assertEqual(len(island['py_verts']), 3)

    # -- 3. Adjacent faces form one island -----------------------------------

    def test_connected_faces_single_island(self):
        """Two quads sharing an edge form a single island."""
        self.bm = bmesh.new()
        v1 = self.bm.verts.new((0.0, 0.0, 0.0))
        v2 = self.bm.verts.new((1.0, 0.0, 0.0))
        v3 = self.bm.verts.new((1.0, 1.0, 0.0))
        v4 = self.bm.verts.new((0.0, 1.0, 0.0))
        v5 = self.bm.verts.new((2.0, 0.0, 0.0))
        v6 = self.bm.verts.new((2.0, 1.0, 0.0))
        self.bm.faces.new([v1, v2, v3, v4])
        self.bm.faces.new([v2, v5, v6, v3])

        islands = _get_face_islands(self.bm, list(self.bm.faces), [])

        self.assertEqual(len(islands), 1)
        self.assertEqual(len(islands[0]['py_faces']), 2)

    # -- 4. Many disconnected islands ----------------------------------------

    def test_many_islands(self):
        """Many disconnected triangles each produce their own island."""
        n = 10
        self.bm = _make_bm_with_islands(n)

        islands = _get_face_islands(self.bm, list(self.bm.faces), [])

        self.assertEqual(len(islands), n)

    # -- 5. Large connected island -------------------------------------------

    def test_large_connected_island(self):
        """A 50x50 grid of quads (2500 faces) forms exactly one island."""
        self.bm = _make_connected_grid(50, 50)

        islands = _get_face_islands(self.bm, list(self.bm.faces), [])

        self.assertEqual(len(islands), 1)
        self.assertEqual(len(islands[0]['py_faces']), 2500)


    # -- 6. Performance benchmarks -------------------------------------------

    # Bump when the implementation changes intentionally, so that CI logs can
    # distinguish a deliberate baseline shift from a regression.
    _PERF_VERSION = 1

    def test_performance_large_connected_island(self):
        """Benchmark _get_face_islands() on a 50x50 quad grid (2500 faces).

        Always passes.  Prints descriptive statistics to stdout so that
        regressions are visible in CI logs without failing the suite.

        All input bmesh objects are created upfront so mesh-creation time
        is excluded from measurements.  A pre-warm phase runs the function
        several times before any timing begins, allowing interpreter and OS
        effects (first-call bytecode compilation, page faults) to settle.
        """
        _N_WARMUP = 5
        _N_TRIALS = 50
        _GRID_SIZE = 50  # 50x50 = 2500 connected quad faces

        n_total = _N_WARMUP + _N_TRIALS
        bms = [_make_connected_grid(_GRID_SIZE, _GRID_SIZE)
               for _ in range(n_total)]
        try:
            for bm in bms[:_N_WARMUP]:
                _get_face_islands(bm, list(bm.faces), [])
            samples = []
            for bm in bms[_N_WARMUP:]:
                faces = list(bm.faces)
                t0 = time.perf_counter()
                _get_face_islands(bm, faces, [])
                t1 = time.perf_counter()
                samples.append(t1 - t0)
        finally:
            for bm in bms:
                bm.free()

        n_faces = _GRID_SIZE * _GRID_SIZE
        mean_ms = statistics.mean(samples) * 1000
        median_ms = statistics.median(samples) * 1000
        stdev_ms = statistics.stdev(samples) * 1000
        min_ms = min(samples) * 1000
        max_ms = max(samples) * 1000

        print(
            f'\n--- _get_face_islands performance v{self._PERF_VERSION}'
            f' ({n_faces} connected faces, {_N_TRIALS} trials) ---\n'
            f'  mean:    {mean_ms:.3f} ms\n'
            f'  median:  {median_ms:.3f} ms\n'
            f'  std dev: {stdev_ms:.3f} ms\n'
            f'  min:     {min_ms:.3f} ms\n'
            f'  max:     {max_ms:.3f} ms'
        )

    def test_performance_many_disconnected_islands(self):
        """Benchmark _get_face_islands() on 11,000 disconnected triangles.

        This exercises the high-island-count case that arises when a mesh is
        split into many separate geometry islands (e.g. after applying an
        EdgeSplit modifier that separates every face).  Each triangle is its
        own island, so the DFS makes 11,000 separate traversals and produces
        11,000 result dicts.

        Always passes.  Prints descriptive statistics so regressions are
        visible in CI logs without failing the suite.
        """
        _N_WARMUP = 5
        _N_TRIALS = 50
        _N_ISLANDS = 11_000

        n_total = _N_WARMUP + _N_TRIALS
        bms = [_make_bm_with_islands(_N_ISLANDS) for _ in range(n_total)]
        try:
            for bm in bms[:_N_WARMUP]:
                _get_face_islands(bm, list(bm.faces), [])
            samples = []
            for bm in bms[_N_WARMUP:]:
                faces = list(bm.faces)
                t0 = time.perf_counter()
                _get_face_islands(bm, faces, [])
                t1 = time.perf_counter()
                samples.append(t1 - t0)
        finally:
            for bm in bms:
                bm.free()

        mean_ms = statistics.mean(samples) * 1000
        median_ms = statistics.median(samples) * 1000
        stdev_ms = statistics.stdev(samples) * 1000
        min_ms = min(samples) * 1000
        max_ms = max(samples) * 1000

        print(
            f'\n--- _get_face_islands performance v{self._PERF_VERSION}'
            f' ({_N_ISLANDS} disconnected triangles, {_N_TRIALS} trials) ---\n'
            f'  mean:    {mean_ms:.3f} ms\n'
            f'  median:  {median_ms:.3f} ms\n'
            f'  std dev: {stdev_ms:.3f} ms\n'
            f'  min:     {min_ms:.3f} ms\n'
            f'  max:     {max_ms:.3f} ms'
        )


if __name__ == '__main__':
    # Strip Blender's argv; everything after '--' is forwarded to unittest.
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
