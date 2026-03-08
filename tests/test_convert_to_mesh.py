"""Tests for OBJECT_OT_convert_to_mesh naming behavior.

Run with headless Blender::

    blender --background --python tests/test_convert_to_mesh.py -- -v
"""
import os
import sys
import types as _types
import unittest

import bpy

# Make the add-on importable as a package.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ADDON_NAME = os.path.basename(_PROJECT_ROOT)
sys.path.insert(0, os.path.dirname(_PROJECT_ROOT))

_addon = __import__(_ADDON_NAME)

_prim_mod = _addon.collider_shapes.add_bounding_primitive
_convert_mod = _addon.collider_conversion.convert_to_mesh
_OBJECT_OT_convert_to_mesh = _convert_mod.OBJECT_OT_convert_to_mesh
_base_package = _convert_mod.base_package


# -- Helpers -----------------------------------------------------------------


def _remove_obj(obj):
    """Remove a Blender object and its mesh data."""
    if obj is None:
        return
    data = obj.data
    bpy.data.objects.remove(obj)
    if isinstance(data, bpy.types.Mesh):
        try:
            bpy.data.meshes.remove(data)
        except Exception:
            pass


# -- Tests -------------------------------------------------------------------


# -- naming: O(N²) → O(N) cache regression -----------------------------------


class TestConvertToMeshNamingIsLinear(unittest.TestCase):
    """execute() must use a naming cache so renaming N colliders costs O(N)
    calls to create_name_number, not O(N²).

    Pre-fix: unique_name() is called without a cache on every iteration, so
    each call restarts the search from count=1 and scans forward past all
    previously renamed objects.  With N objects, total calls ≈ N²/2.

    Post-fix: a cache dict is created before the loop and passed to each
    unique_name() call so the search resumes from the last position.
    Total calls drop to O(N).

    execute() is called directly with a SimpleNamespace context so the test
    does not require full operator registration.  keep_original_material=True
    skips the material block; col_collection_name is set to a sentinel that
    matches no collection so the collection-unlink block is a no-op.
    """

    _N = 20

    def setUp(self):
        self.created_objs = []
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        base = 'ConvToMeshTestCollider'
        for i in range(self._N):
            name = f'{base}_{i:03d}'
            mesh = bpy.data.meshes.new(name + '_mesh')
            obj = bpy.data.objects.new(name, mesh)
            bpy.context.collection.objects.link(obj)
            obj['isCollider'] = True
            obj.select_set(True)
            self.created_objs.append(obj)

    def tearDown(self):
        for obj in list(self.created_objs):
            _remove_obj(obj)
        self.created_objs = []
        if hasattr(self, '_orig_create_name_number'):
            _prim_mod.create_name_number = self._orig_create_name_number

    def test_call_count_is_linear_not_quadratic(self):
        """Total create_name_number() calls for N colliders must be O(N),
        not O(N²)."""
        N = self._N
        call_count = [0]
        orig = _prim_mod.create_name_number
        self._orig_create_name_number = orig

        def counting_wrapper(name, nr, digits=3):
            call_count[0] += 1
            return orig(name, nr, digits)

        _prim_mod.create_name_number = counting_wrapper

        op = _types.SimpleNamespace(
            mesh_name='ConvToMeshTest',
            keep_original_material=True,
            report=lambda level, msg: None,
        )
        ctx = _types.SimpleNamespace(
            scene=_types.SimpleNamespace(simple_collider=_types.SimpleNamespace()),
            preferences=_types.SimpleNamespace(
                addons={_base_package: _types.SimpleNamespace(
                    preferences=_types.SimpleNamespace(col_collection_name='__no_match__')
                )}
            ),
        )
        _OBJECT_OT_convert_to_mesh.execute(op, ctx)

        _prim_mod.create_name_number = orig

        # O(N²) lower bound: N calls each skipping ≥ 0..N-1 already-renamed
        # objects → at least N*(N+1)/2 calls to create_name_number.
        quadratic_lower_bound = N * (N + 1) // 2  # 210 for N=20

        self.assertLess(
            call_count[0],
            quadratic_lower_bound,
            f"execute() made {call_count[0]} calls to create_name_number() for {N} colliders; "
            f"expected < {quadratic_lower_bound} (O(N²) lower bound). "
            "This indicates unique_name() is being called without a cache in the rename loop."
        )


if __name__ == '__main__':
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
