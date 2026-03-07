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

_get_face_islands = _island_mod._get_face_islands
_construct_python_faces = _island_mod.construct_python_faces


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

        islands = _get_face_islands(list(self.bm.faces))

        self.assertEqual(len(islands), 1)
        self.assertEqual(len(islands[0]['py_faces']), 1)
        self.assertEqual(len(islands[0]['py_verts']), 3)

    # -- 2. Two disconnected islands -----------------------------------------

    def test_two_islands(self):
        """Two disconnected triangles produce exactly two islands."""
        self.bm = _make_bm_with_islands(2)

        islands = _get_face_islands(list(self.bm.faces))

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

        islands = _get_face_islands(list(self.bm.faces))

        self.assertEqual(len(islands), 1)
        self.assertEqual(len(islands[0]['py_faces']), 2)

    # -- 4. Many disconnected islands ----------------------------------------

    def test_many_islands(self):
        """Many disconnected triangles each produce their own island."""
        n = 10
        self.bm = _make_bm_with_islands(n)

        islands = _get_face_islands(list(self.bm.faces))

        self.assertEqual(len(islands), n)

    # -- 5. Large connected island -------------------------------------------

    def test_large_connected_island(self):
        """A 50x50 grid of quads (2500 faces) forms exactly one island."""
        self.bm = _make_connected_grid(50, 50)

        islands = _get_face_islands(list(self.bm.faces))

        self.assertEqual(len(islands), 1)
        self.assertEqual(len(islands[0]['py_faces']), 2500)


    # -- 6. Performance benchmarks -------------------------------------------

    # Bump when the implementation changes intentionally, so that CI logs can
    # distinguish a deliberate baseline shift from a regression.
    _PERF_VERSION = 2

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
                _get_face_islands(list(bm.faces))
            samples = []
            for bm in bms[_N_WARMUP:]:
                faces = list(bm.faces)
                t0 = time.perf_counter()
                _get_face_islands(faces)
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
                _get_face_islands(list(bm.faces))
            samples = []
            for bm in bms[_N_WARMUP:]:
                faces = list(bm.faces)
                t0 = time.perf_counter()
                _get_face_islands(faces)
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


class TestConstructPythonFacesLifetime(unittest.TestCase):
    """Vertex coordinates stored by construct_python_faces must be independent
    copies, not live aliases into BMesh-backed memory.

    create_objs_from_island() calls _get_face_islands() (which calls
    construct_python_faces()) and then calls bm.free() *before* reading
    py_verts.  If py_verts holds live BMVert.co references rather than
    copied values (v.co.copy()), two things go wrong:

    1. Mutating a BMVert after the call immediately corrupts the stored coord.
    2. After bm.free() the stored pointers are dangling; on Linux/glibc freed
       pages are quickly zeroed or reused, so vertices collapse to the origin
       or read as garbage.  On Windows/macOS the allocator leaves pages intact
       longer, hiding the bug.

    The aliasing test (case 1) is fully deterministic and does not depend on
    allocator behaviour, so it is the primary regression guard.
    """

    def test_construct_python_faces_copies_vertex_coords(self):
        """py_verts must not alias live BMVert.co memory.

        After construct_python_faces() returns, mutating a BMVert coordinate
        must NOT change the value already stored in py_verts.  If py_verts
        holds a reference to v.co (not a copy), the mutation would be visible.
        """
        bm = bmesh.new()
        try:
            v0 = bm.verts.new((1.0, 2.0, 3.0))
            v1 = bm.verts.new((4.0, 5.0, 6.0))
            v2 = bm.verts.new((7.0, 8.0, 9.0))
            bm.faces.new([v0, v1, v2])

            result = _construct_python_faces(list(bm.faces))

            # Overwrite all three BMVert coordinates with a sentinel value.
            # If py_verts is a list of live references (v.co, not v.co.copy()),
            # reading them now would return (0.0, 0.0, 0.0) rather than the
            # original coordinates.
            v0.co.xyz = (0.0, 0.0, 0.0)
            v1.co.xyz = (0.0, 0.0, 0.0)
            v2.co.xyz = (0.0, 0.0, 0.0)
        finally:
            bm.free()

        py_verts = result['py_verts']
        self.assertEqual(len(py_verts), 3)

        expected = {(1.0, 2.0, 3.0), (4.0, 5.0, 6.0), (7.0, 8.0, 9.0)}
        got = {tuple(v) for v in py_verts}
        self.assertEqual(
            got, expected,
            "py_verts aliased live BMVert.co memory: mutation after "
            "construct_python_faces() changed the stored coordinates.",
        )

    def test_get_face_islands_copies_vertex_coords(self):
        """py_verts from _get_face_islands must not alias live BMVert.co memory.

        Mirrors test_construct_python_faces_copies_vertex_coords but exercises
        the full _get_face_islands() → construct_python_faces() pipeline with
        two disconnected islands, matching the create_objs_from_island() flow.
        """
        bm = bmesh.new()
        try:
            a0 = bm.verts.new((0.0, 0.0, 0.0))
            a1 = bm.verts.new((1.0, 0.0, 0.0))
            a2 = bm.verts.new((0.0, 1.0, 0.0))
            bm.faces.new([a0, a1, a2])

            b0 = bm.verts.new((10.0, 0.0, 0.0))
            b1 = bm.verts.new((11.0, 0.0, 0.0))
            b2 = bm.verts.new((10.0, 1.0, 0.0))
            bm.faces.new([b0, b1, b2])

            islands = _get_face_islands(list(bm.faces))

            # Overwrite all BMVert coords with a sentinel; copies are unaffected.
            for v in (a0, a1, a2, b0, b1, b2):
                v.co.xyz = (0.0, 0.0, 0.0)
        finally:
            bm.free()

        self.assertEqual(len(islands), 2)

        all_verts = set()
        for island in islands:
            for v in island['py_verts']:
                all_verts.add(tuple(v))

        expected = {
            (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
            (10.0, 0.0, 0.0), (11.0, 0.0, 0.0), (10.0, 1.0, 0.0),
        }
        self.assertEqual(
            all_verts, expected,
            "py_verts aliased live BMVert.co memory: mutating verts after "
            "_get_face_islands() changed the stored island coordinates.",
        )


if __name__ == '__main__':
    # Strip Blender's argv; everything after '--' is forwarded to unittest.
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
