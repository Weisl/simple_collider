"""Integration tests for the loose-island modifier-stack path in
OBJECT_OT_add_bounding_object and the edit-mode handling in
create_objs_from_island.

Run with headless Blender::

    blender --background --python tests/test_loose_island_modifier_handling.py
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

_island_mod = _addon.bmesh_operations.mesh_split_by_island
_prim_mod = _addon.collider_shapes.add_bounding_primitive
_OBJECT_OT_add_bounding_object = _prim_mod.OBJECT_OT_add_bounding_object

_create_objs_from_island = _island_mod.create_objs_from_island


# -- Helpers -----------------------------------------------------------------


def _make_multi_island_obj(n_islands):
    """Create a linked Blender object with n_islands disconnected triangles."""
    verts = []
    faces = []
    for i in range(n_islands):
        x = float(i) * 2.0
        base = len(verts)
        verts.extend([(x, 0.0, 0.0), (x + 1.0, 0.0, 0.0), (x, 1.0, 0.0)])
        faces.append([base, base + 1, base + 2])
    mesh = bpy.data.meshes.new('TestIslandMesh')
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new('TestIslandObj', mesh)
    bpy.context.collection.objects.link(obj)
    return obj


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


# -- create_objs_from_island -------------------------------------------------


class TestCreateObjsFromIsland(unittest.TestCase):
    """Tests for create_objs_from_island invoked from OBJECT mode with no
    active operator or edit context."""

    def setUp(self):
        self.obj = _make_multi_island_obj(3)
        bpy.context.view_layer.objects.active = self.obj
        self.obj.select_set(True)
        self.split_objs = []

    def tearDown(self):
        # The pre-fix implementation leaves the object in edit mode; reset it
        # before removing data blocks so cleanup does not raise.
        active = bpy.context.view_layer.objects.active
        if active and active.mode != 'OBJECT':
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except Exception:
                pass
        for obj in self.split_objs:
            _remove_obj(obj)
        self.split_objs = []
        _remove_obj(self.obj)
        self.obj = None

    # -- Mode handling -------------------------------------------------------

    def test_does_not_leave_object_in_edit_mode(self):
        """The source object must remain in OBJECT mode after the call."""
        if self.obj.mode != 'OBJECT':
            self.skipTest("precondition: object must start in OBJECT mode")
        try:
            self.split_objs = _create_objs_from_island(self.obj)
        except Exception as exc:
            self.fail(
                "create_objs_from_island raised unexpectedly: "
                f"{type(exc).__name__}: {exc}"
            )
        self.assertEqual(
            self.obj.mode, 'OBJECT',
            f"create_objs_from_island left the object in {self.obj.mode!r} mode"
        )

    # -- Result count --------------------------------------------------------

    def test_returns_one_object_per_island(self):
        """One output object must be returned per disconnected mesh island."""
        try:
            self.split_objs = _create_objs_from_island(self.obj)
        except Exception as exc:
            self.fail(
                "create_objs_from_island raised unexpectedly: "
                f"{type(exc).__name__}: {exc}"
            )
        self.assertEqual(
            len(self.split_objs), 3,
            "Expected one split object per disconnected island"
        )


# -- get_pre_processed_mesh_objs: modifier-stack guard -----------------------


class _OperatorSpy:
    """Spy stand-in for OBJECT_OT_add_bounding_object.

    Lets get_pre_processed_mesh_objs() be driven with controlled attribute
    state — particularly my_use_modifier_stack — without invoking the full
    modal operator.  Records calls to apply_all_modifiers in
    self.apply_modifier_calls for post-call assertion; all other collaborator
    methods are stubs that satisfy the method's structural requirements.

    All attributes are plain Python values, matching the post-invoke() state
    of the real operator (none go through RNA descriptors).
    """

    def __init__(self, mesh_obj, *, use_modifier_stack):
        self.selected_objects = [mesh_obj]
        self.my_use_modifier_stack = use_modifier_stack
        self.use_loose_mesh = True
        self.obj_mode = 'OBJECT'
        self.creation_mode = ['INDIVIDUAL']
        self.creation_mode_edit = ['INDIVIDUAL']
        self.creation_mode_idx = 0
        self.tmp_meshes = []
        self.my_space = 'WORLD'
        self.use_modifier_stack = use_modifier_stack
        self.prefs = _types.SimpleNamespace(col_tmp_collection_color='NONE')
        self.apply_modifier_calls = []

    def is_valid_object(self, obj):
        return True

    def add_to_collections(self, obj, collection_name, hide=False, color='NONE'):
        # Return a namespace so that `col.color_tag = ...` succeeds without
        # creating real Blender collections that require separate teardown.
        return _types.SimpleNamespace(color_tag=color)

    def apply_all_modifiers(self, context, obj):
        self.apply_modifier_calls.append(obj.name)

    def remove_objects(self, objs):
        pass


class TestApplyModifiersGuard(unittest.TestCase):
    """Tests for the my_use_modifier_stack guard in the loose-island path of
    get_pre_processed_mesh_objs.

    get_pre_processed_mesh_objs is driven directly via _OperatorSpy with
    create_objs_from_island patched out, isolating the modifier-application
    decision from the island-splitting step.
    """

    def setUp(self):
        mesh = bpy.data.meshes.new('TestIslandMesh')
        mesh.from_pydata(
            [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)],
            [],
            [[0, 1, 2, 3]],
        )
        mesh.update()
        self.obj = bpy.data.objects.new('TestIslandObj', mesh)
        bpy.context.collection.objects.link(self.obj)
        bpy.context.view_layer.objects.active = self.obj
        # A modifier gives apply_all_modifiers a meaningful target.
        self.obj.modifiers.new(name='Subd', type='SUBSURF')
        self._spy = None

    def tearDown(self):
        if self._spy is not None:
            for obj in self._spy.tmp_meshes:
                _remove_obj(obj)
            self._spy = None
        _remove_obj(self.obj)
        self.obj = None

    def _run_loose_island_path(self, *, use_modifier_stack):
        """Run get_pre_processed_mesh_objs via the spy; patch out create_objs_from_island."""
        spy = _OperatorSpy(self.obj, use_modifier_stack=use_modifier_stack)
        self._spy = spy
        orig = _prim_mod.create_objs_from_island
        _prim_mod.create_objs_from_island = lambda obj, use_world=True: []
        try:
            _OBJECT_OT_add_bounding_object.get_pre_processed_mesh_objs(
                spy, bpy.context
            )
        finally:
            _prim_mod.create_objs_from_island = orig
        return spy

    # -- Stack disabled ------------------------------------------------------

    def test_modifier_not_applied_when_stack_disabled(self):
        """apply_all_modifiers must not be called when my_use_modifier_stack is False."""
        spy = self._run_loose_island_path(use_modifier_stack=False)
        self.assertEqual(
            spy.apply_modifier_calls, [],
            f"apply_all_modifiers was called despite my_use_modifier_stack=False: {spy.apply_modifier_calls!r}"
        )

    # -- Stack enabled (regression guard) ------------------------------------

    def test_modifier_applied_when_stack_enabled(self):
        """apply_all_modifiers must be called when my_use_modifier_stack is True."""
        spy = self._run_loose_island_path(use_modifier_stack=True)
        self.assertGreater(
            len(spy.apply_modifier_calls), 0,
            f"apply_all_modifiers was not called despite my_use_modifier_stack=True: {spy.apply_modifier_calls!r}"
        )


if __name__ == '__main__':
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
