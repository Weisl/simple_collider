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


# -- _PostprocessingFake ------------------------------------------------------


class _PostprocessingFake:
    """Fake operator that drives primitive_postprocessing() in headless tests.

    Methods that would crash in headless mode (no viewport) are no-ops;
    everything else is the minimal real implementation needed to reach the
    code paths under test.
    """

    def __init__(self, tmp_meshes):
        self.tmp_meshes = tmp_meshes
        self.displace_modifiers = []

        _group = _types.SimpleNamespace(mode='DEFAULT', color=(1.0, 0.5, 0.0, 1.0))
        self.collision_groups = [_group]
        self.collision_group_idx = 0
        self.current_settings_dic = {'alpha': 0.5, 'displace_offset': 0.0}

        self.prefs = _types.SimpleNamespace(
            use_col_collection=False,
            use_parent_to=True,       # True = skip the unparent branch
            wireframe_mode='NEVER',
            debug=False,              # False = the hide loop runs (pre-fix)
            physics_material_name='',
        )

        self.use_weld_modifier = False
        self.use_remesh = False
        self.use_decimation = False
        self.use_geo_nodes_hull = False
        self.use_keep_original_materials = True
        self.keep_original_material = True
        self.shape = 'box_shape'

    def set_object_collider_group(self, obj):
        obj['collider_group'] = self.collision_groups[self.collision_group_idx].mode

    def set_viewport_drawing(self, context, bounding_object):
        # No-op: context.space_data is None in --background mode.
        pass

    def add_displacement_modifier(self, context, bounding_object):
        modifier = bounding_object.modifiers.new(name='Collider_displace', type='DISPLACE')
        modifier.strength = self.current_settings_dic['displace_offset']
        self.displace_modifiers.append(modifier)

    def set_collections(self, obj, collections):
        # No-op: skip collection bookkeeping for this test.
        pass

    def add_to_collections(self, obj, name, **kwargs):
        # No-op: use_col_collection is False so this is never reached.
        pass


def _make_tri_obj(name):
    """Create a single-triangle mesh object linked to the default collection."""
    mesh = bpy.data.meshes.new(name + '_mesh')
    mesh.from_pydata(
        [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.5, 1.0, 0.0)],
        [],
        [[0, 1, 2]],
    )
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


# -- primitive_postprocessing: tmp_meshes hide behaviour ---------------------


def _find_registered_addon_key():
    """Return the key under which simple_collider is registered in
    bpy.context.preferences.addons, or None if it isn't registered.

    In Blender 4.2+ the extension system stores add-ons under the prefix
    'bl_ext.<repo>.<name>' rather than the bare package name.
    """
    for key in bpy.context.preferences.addons.keys():
        if key == _ADDON_NAME or key.endswith('.' + _ADDON_NAME):
            return key
    return None


class TestPrimitivePostprocessingDoesNotHideTmpMeshes(unittest.TestCase):
    """primitive_postprocessing() must not hide tmp_meshes on each call.

    Pre-fix: the method iterates self.tmp_meshes and calls hide_set(True) on
    every entry, so N calls with N objects = N² hide_set() calls.

    Post-fix: the hide loop is moved to reset_to_initial_state(), so
    primitive_postprocessing() leaves tmp_meshes untouched.

    This test detects the pre-fix regression by verifying that after a single
    call to primitive_postprocessing(), no tmp_mesh has been hidden.

    primitive_postprocessing() has a hard-coded lookup into
    bpy.context.preferences.addons[base_package].  In the test environment the
    add-on is imported directly (not enabled via the extension system), so
    _prim_mod.base_package ('simple_collider') may differ from the registered
    extension key ('bl_ext.user_default.simple_collider').  setUpClass patches
    the module-level variable for the duration of the test class and restores
    it in tearDownClass.
    """

    @classmethod
    def setUpClass(cls):
        registered_key = _find_registered_addon_key()
        orig = _prim_mod.base_package
        if registered_key is not None and registered_key != orig:
            _prim_mod.base_package = registered_key
            cls._base_package_patched = orig   # store original to restore
        else:
            cls._base_package_patched = None
        cls._addon_available = (
            registered_key is not None
            and hasattr(bpy.context.scene, 'active_physics_material')
        )

    @classmethod
    def tearDownClass(cls):
        if cls._base_package_patched is not None:
            _prim_mod.base_package = cls._base_package_patched

    def setUp(self):
        self.tmp_objs = []
        self.bounding_obj = None

    def tearDown(self):
        for obj in list(self.tmp_objs):
            _remove_obj(obj)
        self.tmp_objs = []
        if self.bounding_obj is not None:
            _remove_obj(self.bounding_obj)
            self.bounding_obj = None

    def test_does_not_hide_tmp_meshes(self):
        """Calling primitive_postprocessing() once must not hide any tmp_meshes."""
        if not self._addon_available:
            self.skipTest(
                "simple_collider not registered in bpy.context.preferences.addons; "
                "run with the add-on installed or enabled"
            )

        N = 3
        self.tmp_objs = [_make_tri_obj(f'TmpMesh_{i}') for i in range(N)]
        self.bounding_obj = _make_tri_obj('BoundingObj')

        for obj in self.tmp_objs:
            obj.hide_set(False)

        fake = _PostprocessingFake(self.tmp_objs)
        _OBJECT_OT_add_bounding_object.primitive_postprocessing(
            fake, bpy.context, self.bounding_obj, []
        )

        for obj in self.tmp_objs:
            self.assertFalse(
                obj.hide_get(),
                f"{obj.name} was hidden by primitive_postprocessing(); "
                "hiding should only happen in reset_to_initial_state()"
            )


# -- unique_name: O(N²) → O(N) counter-restart regression -------------------


class TestUniqueNameDoesNotRestartCounterPerCall(unittest.TestCase):
    """unique_name() must not restart its search from count=1 on every call.

    Pre-fix: unique_name() resets count=1 at the top of each call, then
    scans bpy.data.objects forward until a free slot is found.  With N calls
    for the same base name, where the first K names are already taken, the
    total number of calls to create_name_number() is
      (K+1) + (K+2) + … + (K+N) ≈ N·K + N²/2  (O(N²)).

    Post-fix: a per-base-name cache remembers the last used index, so each
    subsequent call starts from the cached position.  Total calls to
    create_name_number() drop to O(K + N) where K is the skip over
    pre-existing names.

    The test patches _prim_mod.create_name_number with a counting wrapper to
    measure calls directly, avoiding any dependency on wall-clock time.
    """

    # N pre-existing names in bpy.data.objects; then call unique_name N more times.
    _N = 30

    def setUp(self):
        self.existing_objs = []
        self.base_name = 'UniqueNameTestBase'
        # Create N mesh objects whose names occupy "UniqueNameTestBase_001"
        # through "UniqueNameTestBase_0N" so that any fresh unique_name() call
        # has to skip past them.
        for i in range(1, self._N + 1):
            name = f'{self.base_name}_{i:03d}'
            mesh = bpy.data.meshes.new(name + '_mesh')
            obj = bpy.data.objects.new(name, mesh)
            bpy.context.collection.objects.link(obj)
            self.existing_objs.append(obj)

    def tearDown(self):
        for obj in list(self.existing_objs):
            _remove_obj(obj)
        self.existing_objs = []
        # Restore the real create_name_number (patched in the test body).
        if hasattr(self, '_orig_create_name_number'):
            _prim_mod.create_name_number = self._orig_create_name_number

    def test_call_count_is_linear_not_quadratic(self):
        """Total create_name_number() calls for N sequential unique_name()
        calls must be O(N), not O(N²)."""
        N = self._N
        call_count = [0]
        orig = _prim_mod.create_name_number
        self._orig_create_name_number = orig

        def counting_wrapper(name, nr, digits=3):
            call_count[0] += 1
            return orig(name, nr, digits)

        _prim_mod.create_name_number = counting_wrapper

        cache = {}
        for _ in range(N):
            _OBJECT_OT_add_bounding_object.unique_name(self.base_name, digits=3, cache=cache)

        _prim_mod.create_name_number = orig

        # O(N²) lower bound for pre-fix: N calls each skipping ≥N existing names
        # → at least N*(N+1)/2 calls to create_name_number.
        quadratic_lower_bound = N * (N + 1) // 2  # ~465 for N=30

        self.assertLess(
            call_count[0],
            quadratic_lower_bound,
            f"unique_name() made {call_count[0]} calls to create_name_number() "
            f"for {N} sequential calls with {N} pre-existing names; "
            f"expected < {quadratic_lower_bound} (O(N²) lower bound). "
            "This indicates the counter is being restarted from 1 on each call."
        )


# -- custom_set_parent: correctness regression guard -------------------------


class TestCustomSetParentPreservesTransform(unittest.TestCase):
    """Regression guard for custom_set_parent().

    The fix replaces bpy.ops.object.parent_set() with a direct Python
    assignment that preserves the child's world transform.  These tests verify
    that the direct-assignment approach produces the same observable result as
    the operator did: parent is assigned and the child's world-space position
    is unchanged.
    """

    def setUp(self):
        self.parent_obj = None
        self.child_obj = None

    def tearDown(self):
        if self.child_obj is not None:
            _remove_obj(self.child_obj)
            self.child_obj = None
        if self.parent_obj is not None:
            _remove_obj(self.parent_obj)
            self.parent_obj = None

    def test_child_parent_is_set(self):
        """After custom_set_parent, child.parent must equal parent."""
        self.parent_obj = _make_tri_obj('Parent')
        self.child_obj = _make_tri_obj('Child')

        bpy.context.view_layer.objects.active = self.parent_obj
        self.parent_obj.select_set(True)
        self.child_obj.select_set(True)

        _OBJECT_OT_add_bounding_object.custom_set_parent(
            bpy.context, self.parent_obj, self.child_obj
        )

        self.assertIs(
            self.child_obj.parent,
            self.parent_obj,
            "child.parent was not set to parent after custom_set_parent()"
        )

    def test_child_world_transform_preserved(self):
        """The child's world-space location must be unchanged after reparenting."""
        import mathutils

        self.parent_obj = _make_tri_obj('Parent')
        self.parent_obj.location = (5.0, 3.0, 1.0)
        bpy.context.view_layer.update()

        self.child_obj = _make_tri_obj('Child')
        self.child_obj.location = (2.0, 4.0, 6.0)
        bpy.context.view_layer.update()

        world_before = self.child_obj.matrix_world.copy()

        bpy.context.view_layer.objects.active = self.parent_obj
        self.parent_obj.select_set(True)
        self.child_obj.select_set(True)

        _OBJECT_OT_add_bounding_object.custom_set_parent(
            bpy.context, self.parent_obj, self.child_obj
        )
        bpy.context.view_layer.update()

        world_after = self.child_obj.matrix_world

        for i in range(4):
            for j in range(4):
                self.assertAlmostEqual(
                    world_before[i][j],
                    world_after[i][j],
                    places=5,
                    msg=(
                        f"matrix_world[{i}][{j}] changed after reparenting: "
                        f"{world_before[i][j]:.6f} → {world_after[i][j]:.6f}"
                    ),
                )

    def test_child_world_position_when_location_set_without_depsgraph_update(self):
        """World position must be correct when location is set without a prior
        depsgraph update before custom_set_parent is called.

        Cylinder and sphere colliders set new_collider.location (or
        basic_sphere.location) to the computed centre immediately after an
        operation that triggered a depsgraph evaluation (bpy.ops call or
        objects.link).  The cached matrix_world is therefore stale when
        custom_set_parent runs, reflecting the pre-location-change position
        rather than the intended centre.

        Pre-fix: custom_set_parent reads matrix_world, which is stale (cached
        at origin from the last depsgraph evaluation).  The child is parented
        to the cached origin position, not the intended location.

        Post-fix: the world matrix is built from child.location/rotation/scale,
        which are always current, so the correct position is preserved.
        """
        from mathutils import Vector

        self.parent_obj = _make_tri_obj('Parent')
        bpy.context.view_layer.update()

        # Create the child and force a depsgraph update that caches its
        # matrix_world at the origin — exactly as happens after
        # bpy.context.collection.objects.link() in create_sphere().
        self.child_obj = _make_tri_obj('Child')
        bpy.context.view_layer.update()  # matrix_world cached at (0, 0, 0)

        # Set location to the intended centre WITHOUT another depsgraph update.
        # This mirrors what create_sphere() and generate_cylinder_object() do:
        # they set obj.location after the last depsgraph-updating operation.
        # matrix_world is now stale (still at origin in the cache).
        intended = Vector((3.0, -5.0, 7.0))
        self.child_obj.location = intended

        _OBJECT_OT_add_bounding_object.custom_set_parent(
            bpy.context, self.parent_obj, self.child_obj
        )
        bpy.context.view_layer.update()

        pos = self.child_obj.matrix_world.to_translation()
        for axis, (got, want) in enumerate(zip(pos, intended)):
            self.assertAlmostEqual(
                got, want, places=5,
                msg=(
                    f"World position axis {axis}: expected {want:.6f}, got {got:.6f}. "
                    "custom_set_parent captured a stale matrix_world instead of "
                    "the current child.location."
                ),
            )


if __name__ == '__main__':
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
