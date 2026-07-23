"""Tests for the standalone Collider Cleanup helpers used both by the manual
"object.adjust_decimation" / "object.origin_to_parent" operators and by the
optional auto-apply pass that runs them automatically after collider creation
(see collider_shapes/add_bounding_primitive.py, Pass 3 of the modal confirm
block, gated by prefs.auto_apply_tris_limit / prefs.auto_apply_origin_to_parent).

Run with headless Blender::

    blender --background --python tests/test_auto_apply_cleanup.py
"""
import os
import sys
import unittest

import bmesh
import bpy

# Make the add-on importable as a package.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ADDON_NAME = os.path.basename(_PROJECT_ROOT)
sys.path.insert(0, os.path.dirname(_PROJECT_ROOT))

_addon = __import__(_ADDON_NAME)

_util_mod = _addon.collider_operators.utility_operators
_set_triangle_count_limit = _util_mod.set_triangle_count_limit
_move_origin_to_parent = _util_mod.move_origin_to_parent
_DECIMATE_NAME = _addon.properties.constants.DECIMATE_NAME


class _CleanupObjTestCase(unittest.TestCase):
    """Shared object-creation/teardown helpers."""

    _PREFIX = '__test_autoapply_'

    def setUp(self):
        self._obj_names = []

    def tearDown(self):
        for name in self._obj_names:
            obj = bpy.data.objects.get(name)
            if obj is not None:
                data = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                if isinstance(data, bpy.types.Mesh):
                    mesh = bpy.data.meshes.get(data.name)
                    if mesh is not None:
                        bpy.data.meshes.remove(mesh)

    def _make_empty(self, suffix, location=(0.0, 0.0, 0.0), rotation=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0)):
        obj = bpy.data.objects.new(f'{self._PREFIX}empty_{suffix}', None)
        obj.location = location
        obj.rotation_euler = rotation
        obj.scale = scale
        bpy.context.scene.collection.objects.link(obj)
        self._obj_names.append(obj.name)
        return obj

    def _make_grid(self, suffix, segments=40, size=1.0):
        """A dense quad grid, well above any small triangle target."""
        mesh = bpy.data.meshes.new(f'{self._PREFIX}mesh_{suffix}')
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=segments, y_segments=segments, size=size)
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        obj = bpy.data.objects.new(f'{self._PREFIX}grid_{suffix}', mesh)
        bpy.context.scene.collection.objects.link(obj)
        self._obj_names.append(obj.name)
        return obj

    def _make_single_triangle(self, suffix):
        mesh = bpy.data.meshes.new(f'{self._PREFIX}tri_{suffix}')
        mesh.from_pydata([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)], [], [[0, 1, 2]])
        mesh.update()
        obj = bpy.data.objects.new(f'{self._PREFIX}tri_obj_{suffix}', mesh)
        bpy.context.scene.collection.objects.link(obj)
        self._obj_names.append(obj.name)
        return obj

    @staticmethod
    def _eval_tri_count(obj):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)
        mesh = obj_eval.to_mesh()
        count = sum(len(p.vertices) - 2 for p in mesh.polygons)
        obj_eval.to_mesh_clear()
        return count


class TestSetTriangleCountLimit(_CleanupObjTestCase):

    def test_reaches_target_on_dense_mesh(self):
        obj = self._make_grid('reachable', segments=40)
        original_count = self._eval_tri_count(obj)
        target = 100
        self.assertGreater(original_count, target, "grid fixture must start above the target for this test")

        reached = _set_triangle_count_limit(obj, target)

        self.assertTrue(reached)
        self.assertLessEqual(self._eval_tri_count(obj), target)
        self.assertIsNotNone(obj.modifiers.get(_DECIMATE_NAME))

    def test_already_within_budget_leaves_ratio_at_one(self):
        obj = self._make_grid('within_budget', segments=2)
        original_count = self._eval_tri_count(obj)

        reached = _set_triangle_count_limit(obj, original_count + 1000)

        self.assertTrue(reached)
        decimate = obj.modifiers.get(_DECIMATE_NAME)
        self.assertIsNotNone(decimate)
        self.assertEqual(decimate.ratio, 1.0)

    def test_unreachable_target_returns_false(self):
        obj = self._make_single_triangle('unreachable')

        reached = _set_triangle_count_limit(obj, 0)

        self.assertFalse(reached)

    def test_non_mesh_object_is_a_noop(self):
        obj = self._make_empty('non_mesh')

        reached = _set_triangle_count_limit(obj, 10)

        self.assertTrue(reached)

    def test_reuses_existing_decimate_modifier_by_name(self):
        obj = self._make_grid('reuse', segments=40)
        obj.modifiers.new(name=_DECIMATE_NAME, type='DECIMATE')
        self.assertEqual(len(obj.modifiers), 1)

        _set_triangle_count_limit(obj, 100)

        self.assertEqual(len(obj.modifiers), 1, "should reuse the existing modifier, not add a second one")


class TestMoveOriginToParent(_CleanupObjTestCase):

    def _make_child(self, suffix, parent, location=(2.0, -1.0, 0.5), rotation=(0.0, 0.0, 0.0)):
        mesh = bpy.data.meshes.new(f'{self._PREFIX}childmesh_{suffix}')
        mesh.from_pydata(
            [(-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5),
             (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5)],
            [], [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)],
        )
        mesh.update()
        obj = bpy.data.objects.new(f'{self._PREFIX}child_{suffix}', mesh)
        obj.location = location
        obj.rotation_euler = rotation
        bpy.context.scene.collection.objects.link(obj)
        bpy.context.view_layer.update()
        obj.parent = parent
        bpy.context.view_layer.update()
        self._obj_names.append(obj.name)
        return obj

    @staticmethod
    def _world_verts(obj):
        return [obj.matrix_world @ v.co for v in obj.data.vertices]

    def test_matrix_world_matches_parent_after_move(self):
        parent = self._make_empty('parent_a', location=(1.0, 2.0, 3.0), rotation=(0.1, 0.2, 0.3))
        child = self._make_child('a', parent)

        _move_origin_to_parent(child)

        for row in range(4):
            for col in range(4):
                self.assertAlmostEqual(
                    child.matrix_world[row][col], parent.matrix_world[row][col], places=5,
                    msg=f"matrix_world[{row}][{col}] does not match parent after move_origin_to_parent",
                )

    def test_world_space_appearance_is_preserved(self):
        parent = self._make_empty('parent_b', location=(-1.0, 0.5, 2.0), rotation=(0.2, 0.0, 0.4))
        child = self._make_child('b', parent, location=(3.0, -2.0, 1.0), rotation=(0.0, 0.3, 0.0))

        before = self._world_verts(child)
        _move_origin_to_parent(child)
        after = self._world_verts(child)

        for idx, (v_before, v_after) in enumerate(zip(before, after)):
            for axis in range(3):
                self.assertAlmostEqual(
                    v_before[axis], v_after[axis], places=5,
                    msg=f"vertex {idx}[{axis}] moved: world-space appearance must stay unchanged",
                )

    def test_unparented_object_is_a_noop(self):
        obj = self._make_child('unparented', parent=None)
        obj.parent = None
        before = obj.matrix_world.copy()

        _move_origin_to_parent(obj)

        self.assertEqual(obj.matrix_world, before)


if __name__ == '__main__':
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
