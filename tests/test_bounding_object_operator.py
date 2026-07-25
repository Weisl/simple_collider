"""Integration tests for the loose-island modifier-stack path in
OBJECT_OT_add_bounding_object and the edit-mode handling in
create_objs_from_island.

Run with headless Blender::

    blender --background --python tests/test_loose_island_modifier_handling.py
"""
import math
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

    def add_to_collections(self, context, obj, collection_name, hide=False, color='NONE'):
        # Return a namespace so that `col.color_tag = ...` succeeds without
        # creating real Blender collections that require separate teardown.
        return _types.SimpleNamespace(color_tag=color)

    def apply_all_modifiers(self, context, obj, cache_key=None):
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

    def add_to_collections(self, context, obj, name, **kwargs):
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


# -- unique_name: cache robustness across a sparse name gap -------------------


class TestUniqueNameCacheHandlesGaps(unittest.TestCase):
    """unique_name() with a cache must not return a duplicate when a
    pre-existing name falls exactly on the slot the cache predicts next.

    Scenario: _001–_003 and _007 already exist.  Generating 4 new names must
    yield _004, _005, _006, _008 — skipping the occupied _007 even though the
    cache would otherwise predict it as the next free slot.
    """

    def test_no_duplicates_across_gap(self):
        """4 sequential unique_name() calls must skip _007 (already occupied)
        and return _004, _005, _006, _008 in that order."""
        base = 'UniqueNameGapTestBase'
        pre_existing_names = [
            f'{base}_001', f'{base}_002', f'{base}_003', f'{base}_007',
        ]
        expected = [
            f'{base}_004', f'{base}_005', f'{base}_006', f'{base}_008',
        ]
        created = []
        try:
            for name in pre_existing_names:
                mesh = bpy.data.meshes.new(name + '_mesh')
                obj = bpy.data.objects.new(name, mesh)
                bpy.context.collection.objects.link(obj)
                created.append(obj)

            cache = {}
            generated = []
            for _ in range(4):
                name = _OBJECT_OT_add_bounding_object.unique_name(base, digits=3, cache=cache)
                # Register each generated name immediately so subsequent calls
                # see it as taken, matching real operator usage.
                mesh = bpy.data.meshes.new(name + '_mesh')
                obj = bpy.data.objects.new(name, mesh)
                bpy.context.collection.objects.link(obj)
                created.append(obj)
                generated.append(name)
        finally:
            for obj in created:
                _remove_obj(obj)

        self.assertEqual(generated, expected)


# -- remove_objects: mesh data cleanup ----------------------------------------


class TestRemoveObjectsCleansUpMeshData(unittest.TestCase):
    """remove_objects() must remove associated mesh data blocks alongside objects.

    Pre-fix: bpy.data.objects.remove(ob, do_unlink=True) is called individually
    for each object, leaving bpy.types.Mesh data blocks orphaned in
    bpy.data.meshes (users == 0, but still present and discoverable via
    bpy.data.meshes.get()).

    Post-fix: the method also batch-removes mesh data blocks that are
    exclusively owned by the removed objects (users == 1), so they are
    absent from bpy.data.meshes immediately after the call.  Mesh data
    shared with other objects is left untouched.
    """

    _PREFIX = '__test_rmobjs_'

    def setUp(self):
        self._obj_names = []
        self._mesh_names = []

    def tearDown(self):
        for name in self._obj_names:
            obj = bpy.data.objects.get(name)
            if obj is not None:
                bpy.data.objects.remove(obj, do_unlink=True)
        for name in self._mesh_names:
            mesh = bpy.data.meshes.get(name)
            if mesh is not None:
                bpy.data.meshes.remove(mesh)

    def _make_mesh_obj(self, index):
        mesh = bpy.data.meshes.new(f'{self._PREFIX}{index}')
        obj = bpy.data.objects.new(f'{self._PREFIX}obj_{index}', mesh)
        bpy.context.scene.collection.objects.link(obj)
        self._obj_names.append(obj.name)
        self._mesh_names.append(mesh.name)
        return obj

    def test_mesh_data_removed_with_objects(self):
        """Mesh data blocks exclusively owned by removed objects must be deleted."""
        N = 5
        objs = [self._make_mesh_obj(i) for i in range(N)]
        mesh_names = [obj.data.name for obj in objs]

        _OBJECT_OT_add_bounding_object.remove_objects(objs)

        for name in mesh_names:
            self.assertIsNone(
                bpy.data.meshes.get(name),
                f"Orphaned mesh data block '{name}' was not removed by remove_objects()"
            )

    def test_shared_mesh_data_not_removed(self):
        """Mesh data shared by multiple objects must survive remove_objects().

        remove_objects() only removes mesh data with users == 1.  If a mesh
        is still referenced by a second object, it must remain in
        bpy.data.meshes after the call.
        """
        shared_mesh_name = f'{self._PREFIX}shared'
        shared_mesh = bpy.data.meshes.new(shared_mesh_name)
        self._mesh_names.append(shared_mesh_name)

        obj1 = bpy.data.objects.new(f'{self._PREFIX}shared_obj1', shared_mesh)
        obj2 = bpy.data.objects.new(f'{self._PREFIX}shared_obj2', shared_mesh)
        bpy.context.scene.collection.objects.link(obj1)
        bpy.context.scene.collection.objects.link(obj2)
        self._obj_names.extend([obj1.name, obj2.name])

        # Remove only obj1; shared_mesh still has obj2 as a user.
        _OBJECT_OT_add_bounding_object.remove_objects([obj1])

        self.assertIsNotNone(
            bpy.data.meshes.get(shared_mesh_name),
            f"Shared mesh data block '{shared_mesh_name}' was incorrectly "
            "removed by remove_objects() despite still being used by another object"
        )

    def test_handles_stale_object_reference(self):
        """remove_objects() must not raise on stale StructRNA references.

        When execute() re-runs (e.g. on Use Modifiers toggle), self.tmp_meshes
        may contain Python references to objects already removed by a previous
        pass: get_pre_processed_mesh_objs() appends tmp_ob to tmp_meshes then
        removes it via remove_objects() when use_modifier_stack and
        my_use_modifier_stack are both enabled.  The next call to
        remove_objects(self.tmp_meshes) must skip those stale entries
        silently rather than raising ReferenceError.
        """
        obj = self._make_mesh_obj(99)
        # Remove the underlying Blender object, leaving the Python wrapper stale.
        bpy.data.objects.remove(obj, do_unlink=True)
        # remove_objects() must handle the stale reference without raising.
        try:
            _OBJECT_OT_add_bounding_object.remove_objects([obj])
        except ReferenceError:
            self.fail(
                "remove_objects() raised ReferenceError on a stale StructRNA reference"
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


# -- fix_inverse_matrix: batch update support ---------------------------------

_fix_inverse_matrix = _addon.collider_operators.utility_operators.fix_inverse_matrix
_set_origin_to_com = _prim_mod.set_origin_to_center_of_mass


class TestFixInverseMatrixUpdateDepsgraph(unittest.TestCase):
    """fix_inverse_matrix() must accept update_depsgraph=False and produce the
    same mesh and transform result as update_depsgraph=True.

    Pre-fix: the function has no update_depsgraph parameter, so calling it with
    that keyword raises TypeError.  The confirmation loop in
    add_bounding_primitive.py called view_layer.update() once per collider (N
    evaluations), and fix_inverse_matrix() called it again internally (another
    N), for 2N total — 20,000 evaluations for 10k islands.

    Post-fix: passing update_depsgraph=False skips the internal update, letting
    the caller do one batch update after processing all N objects.  The mesh and
    transform must be identical to the per-call-update path.
    """

    _PREFIX = '__test_fixinv_'

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

    def _make_parent(self, suffix, location):
        obj = bpy.data.objects.new(f'{self._PREFIX}parent_{suffix}', None)
        obj.location = location
        bpy.context.scene.collection.objects.link(obj)
        self._obj_names.append(obj.name)
        return obj

    def _make_child(self, suffix, parent, world_location):
        mesh = bpy.data.meshes.new(f'{self._PREFIX}mesh_{suffix}')
        mesh.from_pydata([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)], [], [[0, 1, 2]])
        mesh.update()
        obj = bpy.data.objects.new(f'{self._PREFIX}child_{suffix}', mesh)
        obj.location = world_location
        bpy.context.scene.collection.objects.link(obj)
        _OBJECT_OT_add_bounding_object.custom_set_parent(bpy.context, parent, obj)
        bpy.context.view_layer.update()
        if obj.parent is not parent:
            self.skipTest(
                "precondition violated: custom_set_parent() did not set parent; "
                "TestCustomSetParentPreservesTransform covers that assumption"
            )
        self._obj_names.append(obj.name)
        return obj

    def test_batched_result_matches_individual(self):
        """Batch mode (update_depsgraph=False + single update) must give the
        same vertex positions and matrix_world as the per-call update path."""
        parent = self._make_parent('b', (2.0, 3.0, 1.0))
        bpy.context.view_layer.update()

        # Individual path: one depsgraph update per call (current/existing behaviour)
        child_individual = self._make_child('b_ind', parent, (1.0, 2.0, 0.0))
        _fix_inverse_matrix(child_individual)
        verts_individual = [v.co.copy() for v in child_individual.data.vertices]
        mw_individual = child_individual.matrix_world.copy()

        # Batch path: skip per-call update, do one update at the end
        child_batched = self._make_child('b_bat', parent, (1.0, 2.0, 0.0))
        _fix_inverse_matrix(child_batched, update_depsgraph=False)
        bpy.context.view_layer.update()
        verts_batched = [v.co.copy() for v in child_batched.data.vertices]
        mw_batched = child_batched.matrix_world.copy()

        for idx, (v_ind, v_bat) in enumerate(zip(verts_individual, verts_batched)):
            for axis in range(3):
                self.assertAlmostEqual(
                    v_ind[axis], v_bat[axis], places=5,
                    msg=(
                        f"vertex {idx}[{axis}]: individual={v_ind[axis]:.6f} "
                        f"vs batched={v_bat[axis]:.6f}"
                    ),
                )
        for row in range(4):
            for col in range(4):
                self.assertAlmostEqual(
                    mw_individual[row][col], mw_batched[row][col], places=5,
                    msg=(
                        f"matrix_world[{row}][{col}]: "
                        f"individual={mw_individual[row][col]:.6f} "
                        f"vs batched={mw_batched[row][col]:.6f}"
                    ),
                )


# -- fix_inverse_matrix: must not bake rotation/location into mesh data -------


class TestFixInverseMatrixPreservesTransform(unittest.TestCase):
    """fix_inverse_matrix() must clear matrix_parent_inverse by re-expressing
    the parent-relative transform on obj.location/rotation_euler/scale, not by
    baking it into the mesh and zeroing the transform.

    Regression for: a rotated, off-centre box collider (e.g. an oriented
    bounding box, or any box with "Recenter Origin" applied) lost both its
    origin location and its rotation after the parent-inverse fix ran, because
    the old implementation baked the local rotation/offset into the mesh
    vertices and reset the object's own transform to identity. That leaves the
    mesh's local vertices no longer forming an axis-aligned box, which breaks
    engines (e.g. Unreal's UBX_/USP_/UCP_ collision convention) that read the
    primitive's shape from local vertex data and its placement from the
    object's transform.
    """

    _PREFIX = '__test_fixinv_preserve_'

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

    def _make_parent(self, suffix, location, rotation):
        obj = bpy.data.objects.new(f'{self._PREFIX}parent_{suffix}', None)
        obj.location = location
        obj.rotation_euler = rotation
        bpy.context.scene.collection.objects.link(obj)
        self._obj_names.append(obj.name)
        return obj

    @staticmethod
    def _box_verts():
        """Unit box, corners at the extremes on every axis -- mirrors a UBX_ box collider."""
        return (
            [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
             (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)],
            [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)],
        )

    @staticmethod
    def _cylinder_verts(radius=1.0, height=2.0, segments=12):
        """Upright cylinder (two rings on the local Z axis) -- mirrors a UCP_ capsule/cylinder
        collider, which must stay axis-aligned along local Z."""
        verts = []
        for z in (-height / 2, height / 2):
            for i in range(segments):
                a = 2 * math.pi * i / segments
                verts.append((radius * math.cos(a), radius * math.sin(a), z))
        faces = []
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((i, j, segments + j, segments + i))
        faces.append(tuple(range(segments)))
        faces.append(tuple(range(2 * segments - 1, segments - 1, -1)))
        return verts, faces

    @staticmethod
    def _sphere_verts(radius=1.0, rings=6, segments=8):
        """Sphere centred on the local origin -- mirrors a USP_ sphere collider."""
        verts = [(0, 0, -radius)]
        for ring in range(1, rings):
            phi = math.pi * ring / rings
            z = radius * math.cos(phi)
            r = radius * math.sin(phi)
            for seg in range(segments):
                theta = 2 * math.pi * seg / segments
                verts.append((r * math.cos(theta), r * math.sin(theta), z))
        verts.append((0, 0, radius))
        # Face winding doesn't matter for these tests (only vertex positions are checked).
        return verts, []

    def _make_child(self, suffix, parent, verts_faces, location, rotation):
        """Parent a mesh built from (verts, faces) and then give it an offset
        origin + custom rotation -- mirroring Recenter Origin + an oriented
        collider (e.g. a minimum/oriented bounding box)."""
        verts, faces = verts_faces
        mesh = bpy.data.meshes.new(f'{self._PREFIX}mesh_{suffix}')
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(f'{self._PREFIX}child_{suffix}', mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
        bpy.context.view_layer.update()

        obj.location = location
        obj.rotation_euler = rotation
        bpy.context.view_layer.update()
        self._obj_names.append(obj.name)
        return obj

    @staticmethod
    def _is_axis_aligned_box(obj):
        xs, ys, zs = zip(*(tuple(v.co) for v in obj.data.vertices))
        return all(len({round(v, 6) for v in axis}) <= 2 for axis in (xs, ys, zs))

    @staticmethod
    def _cylinder_axis_alignment_error(obj):
        """0 for an upright cylinder (constant radius per Z ring); grows if the
        local axis has been tilted."""
        radii_by_z = {}
        for v in obj.data.vertices:
            z = round(v.co.z, 5)
            radii_by_z.setdefault(z, []).append(math.hypot(v.co.x, v.co.y))
        return max(max(rs) - min(rs) for rs in radii_by_z.values())

    @staticmethod
    def _sphere_shape_error(obj):
        """0 for a sphere centred on the local origin; grows if the centre has
        shifted away from the local origin."""
        dists = [v.co.length for v in obj.data.vertices]
        return max(dists) - min(dists)

    @staticmethod
    def _world_verts(obj):
        return [obj.matrix_world @ v.co for v in obj.data.vertices]

    def _assert_transform_preserved_not_baked(self, child, shape_error_fn, shape_error_msg):
        shape_error_before = shape_error_fn(child)
        local_verts_before = [v.co.copy() for v in child.data.vertices]
        world_verts_before = self._world_verts(child)

        _fix_inverse_matrix(child, update_depsgraph=False)
        bpy.context.view_layer.update()

        self.assertTrue(child.matrix_parent_inverse.is_identity)

        # Mesh data must be untouched -- rotation/offset must live on the
        # object's transform, not be baked into vertex coordinates.
        for v_before, v_after in zip(local_verts_before, child.data.vertices):
            for axis in range(3):
                self.assertAlmostEqual(v_before[axis], v_after.co[axis], places=6)
        self.assertAlmostEqual(shape_error_before, shape_error_fn(child), places=4, msg=shape_error_msg)

        # World-space placement must be unchanged.
        for v_before, v_after in zip(world_verts_before, self._world_verts(child)):
            self.assertAlmostEqual((v_before - v_after).length, 0.0, places=4)

        # The collider's own origin/rotation must not collapse to the
        # parent's origin / identity rotation.
        self.assertGreater(child.location.length, 1e-4)
        self.assertGreater(child.rotation_euler.to_quaternion().angle, 1e-4)

    def test_rotated_offset_box_keeps_shape_and_transform(self):
        parent = self._make_parent(
            'box', location=(2.0, 3.0, 1.0),
            rotation=(math.radians(30), math.radians(15), 0.0),
        )
        child = self._make_child(
            'box', parent, self._box_verts(),
            location=(0.3, -0.2, 0.1), rotation=(0.0, 0.0, math.radians(45)),
        )
        self.assertTrue(
            self._is_axis_aligned_box(child),
            "test setup precondition: child mesh must start as an axis-aligned box",
        )
        self._assert_transform_preserved_not_baked(
            child,
            lambda o: 0.0 if self._is_axis_aligned_box(o) else 1.0,
            "mesh must remain an axis-aligned box in local space after the fix",
        )

    def test_rotated_offset_cylinder_keeps_shape_and_transform(self):
        parent = self._make_parent(
            'cyl', location=(2.0, 3.0, 1.0),
            rotation=(math.radians(30), math.radians(15), 0.0),
        )
        child = self._make_child(
            'cyl', parent, self._cylinder_verts(),
            location=(0.3, -0.2, 0.1), rotation=(0.0, 0.0, math.radians(45)),
        )
        self._assert_transform_preserved_not_baked(
            child,
            self._cylinder_axis_alignment_error,
            "cylinder/capsule must stay upright (axis-aligned along local Z) after the fix",
        )

    def test_rotated_offset_sphere_keeps_shape_and_transform(self):
        parent = self._make_parent(
            'sph', location=(2.0, 3.0, 1.0),
            rotation=(math.radians(30), math.radians(15), 0.0),
        )
        child = self._make_child(
            'sph', parent, self._sphere_verts(),
            location=(0.3, -0.2, 0.1), rotation=(0.0, 0.0, math.radians(45)),
        )
        self._assert_transform_preserved_not_baked(
            child,
            self._sphere_shape_error,
            "sphere must stay centred on the local origin after the fix",
        )


# -- fix_parent_inverse_transform: shear-aware skip ---------------------------

_fix_inverse_matrix_is_safe = _addon.collider_operators.utility_operators.fix_inverse_matrix_is_safe
_COLLISION_OT_FixColliderTransform = _addon.collider_operators.utility_operators.COLLISION_OT_FixColliderTransform


def _select_only(*objs):
    """Deselect everything, then select and activate the given objects."""
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


class TestFixColliderTransformSkipsShearedTransforms(unittest.TestCase):
    """object.fix_parent_inverse_transform must skip (and warn about) colliders
    whose parent-relative transform contains shear that Blender's loc/rot/scale
    decomposition can't represent, and fix everything else.

    obj.matrix_world already equals parent.matrix_world @ matrix_parent_inverse
    @ matrix_basis, so the parent's *current* world matrix always cancels out
    of fix_inverse_matrix()'s math. What determines safety is whether
    matrix_parent_inverse -- frozen at whatever moment it was last set -- itself
    contains shear. A parent.scale check (the earlier approach) gets this wrong
    in both directions: it needlessly skips safe cases where the parent was
    scaled non-uniformly well after parenting, and it silently waves through
    unsafe cases where the parent was non-uniform+rotated at parenting time and
    later reset to a uniform scale. These tests cover both failure modes.
    """

    _PREFIX = '__test_fixshear_'

    @classmethod
    def setUpClass(cls):
        bpy.utils.register_class(_COLLISION_OT_FixColliderTransform)

    @classmethod
    def tearDownClass(cls):
        bpy.utils.unregister_class(_COLLISION_OT_FixColliderTransform)

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

    def _make_parent(self, suffix, location=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0), rotation=(0.0, 0.0, 0.0)):
        obj = bpy.data.objects.new(f'{self._PREFIX}parent_{suffix}', None)
        obj.location = location
        obj.scale = scale
        obj.rotation_euler = rotation
        bpy.context.scene.collection.objects.link(obj)
        self._obj_names.append(obj.name)
        return obj

    def _make_child(self, suffix, parent, location=(0.3, 0.4, 0.2), rotation=(0.0, 0.0, 0.0)):
        """Create a mesh child and parent it now, freezing matrix_parent_inverse
        against the parent's *current* matrix_world (mirrors what a real
        parenting operation does)."""
        mesh = bpy.data.meshes.new(f'{self._PREFIX}mesh_{suffix}')
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
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
        bpy.context.view_layer.update()
        self._obj_names.append(obj.name)
        return obj

    @staticmethod
    def _world_verts(obj):
        return [obj.matrix_world @ v.co for v in obj.data.vertices]

    def test_direct_non_uniform_scale_no_rotation_is_fixed(self):
        """Non-uniform scale alone, with no rotation anywhere in the chain,
        never produces shear -- must be fixed, not skipped."""
        parent = self._make_parent('direct_nonuniform', scale=(1.0, 2.0, 3.0))
        child = self._make_child('direct_nonuniform', parent)
        self.assertTrue(_fix_inverse_matrix_is_safe(child))

        before = self._world_verts(child)
        _select_only(child)
        bpy.ops.object.fix_parent_inverse_transform()
        after = self._world_verts(child)

        self.assertTrue(child.matrix_parent_inverse.is_identity)
        for v_before, v_after in zip(before, after):
            self.assertAlmostEqual((v_before - v_after).length, 0.0, places=4)

    def test_direct_non_uniform_scale_with_rotation_is_skipped(self):
        """Non-uniform scale combined with rotation produces real shear that
        Blender's decomposition cannot represent -- must be skipped untouched."""
        parent = self._make_parent(
            'direct_nonuniform_rot', scale=(1.0, 2.0, 3.0),
            rotation=(math.radians(20), math.radians(10), 0.0),
        )
        child = self._make_child('direct_nonuniform_rot', parent, rotation=(0.0, 0.0, math.radians(25)))
        self.assertFalse(_fix_inverse_matrix_is_safe(child))

        mpi_before = child.matrix_parent_inverse.copy()
        verts_before = [v.co.copy() for v in child.data.vertices]

        _select_only(child)
        bpy.ops.object.fix_parent_inverse_transform()

        self.assertEqual(child.matrix_parent_inverse, mpi_before)
        for v_before, v_after in zip(verts_before, child.data.vertices):
            for axis in range(3):
                self.assertAlmostEqual(v_before[axis], v_after.co[axis], places=6)

    def test_parent_scaled_non_uniform_after_parenting_is_still_safe(self):
        """Regression: a parent.scale-only check would skip this (parent reads
        non-uniform right now), but it's actually safe -- matrix_parent_inverse
        was frozen while the parent was still uniform, and the parent's
        *current* scale cancels out of fix_inverse_matrix()'s math regardless
        of what it is."""
        parent = self._make_parent('mutated_after', scale=(1.0, 1.0, 1.0))
        child = self._make_child('mutated_after', parent)

        # Mutate the parent non-uniformly + add rotation AFTER matrix_parent_inverse froze.
        parent.scale = (2.0, 0.5, 1.0)
        parent.rotation_euler = (0.0, 0.4, 0.0)
        bpy.context.view_layer.update()

        self.assertTrue(
            _fix_inverse_matrix_is_safe(child),
            "matrix_parent_inverse was frozen while the parent was still uniform; "
            "the parent's current (mutated) scale must not block the fix",
        )

        before = self._world_verts(child)
        _select_only(child)
        bpy.ops.object.fix_parent_inverse_transform()
        after = self._world_verts(child)

        self.assertTrue(child.matrix_parent_inverse.is_identity)
        for v_before, v_after in zip(before, after):
            self.assertAlmostEqual((v_before - v_after).length, 0.0, places=4)

    def test_parent_reset_to_uniform_after_shear_was_frozen_is_still_skipped(self):
        """Regression: a parent.scale-only check would wave this through (the
        parent reads uniform right now), but matrix_parent_inverse froze real
        shear back when the parent was non-uniform+rotated -- fixing it would
        corrupt the mesh. This is the dangerous false-negative a scale-only
        check misses silently."""
        parent = self._make_parent(
            'shear_then_reset', scale=(1.0, 3.0, 0.4),
            rotation=(math.radians(25), math.radians(15), 0.0),
        )
        child = self._make_child('shear_then_reset', parent, rotation=(0.0, 0.0, math.radians(20)))

        # Reset the parent back to a uniform scale. matrix_parent_inverse keeps
        # the shear from when it was frozen.
        parent.scale = (2.0, 2.0, 2.0)
        bpy.context.view_layer.update()

        self.assertFalse(
            _fix_inverse_matrix_is_safe(child),
            "parent.scale reads uniform now, but matrix_parent_inverse still "
            "carries shear frozen from when the parent was non-uniform+rotated",
        )

        mpi_before = child.matrix_parent_inverse.copy()
        verts_before = [v.co.copy() for v in child.data.vertices]

        _select_only(child)
        bpy.ops.object.fix_parent_inverse_transform()

        self.assertEqual(child.matrix_parent_inverse, mpi_before)
        for v_before, v_after in zip(verts_before, child.data.vertices):
            for axis in range(3):
                self.assertAlmostEqual(v_before[axis], v_after.co[axis], places=6)


# -- set_origin_to_center_of_mass: pre-fetched depsgraph ----------------------


class TestSetOriginToCoMDepsgraphParam(unittest.TestCase):
    """set_origin_to_center_of_mass must accept an optional depsgraph argument.

    Pre-fix: the function always calls bpy.context.evaluated_depsgraph_get()
    internally.  In the confirmation loop each preceding obj.location = com
    dirtied the depsgraph, causing the next call to force a full scene
    re-evaluation — O(N) per call × N calls = O(N²) depsgraph work for N
    colliders.

    Post-fix: an explicit depsgraph parameter can be passed, letting the caller
    hoist evaluated_depsgraph_get() to a single call before the loop.  The
    result must be identical to the per-call path.
    """

    _PREFIX = '__test_com_'

    def setUp(self):
        self._obj_names = []
        self._mesh_names = []

    def tearDown(self):
        for name in self._obj_names:
            obj = bpy.data.objects.get(name)
            if obj is not None:
                bpy.data.objects.remove(obj, do_unlink=True)
        for name in self._mesh_names:
            mesh = bpy.data.meshes.get(name)
            if mesh is not None:
                bpy.data.meshes.remove(mesh)

    def _make_tri_mesh(self, suffix):
        mesh = bpy.data.meshes.new(f'{self._PREFIX}mesh_{suffix}')
        mesh.from_pydata(
            [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (1.0, 2.0, 0.0)], [], [[0, 1, 2]]
        )
        mesh.update()
        obj = bpy.data.objects.new(f'{self._PREFIX}obj_{suffix}', mesh)
        bpy.context.scene.collection.objects.link(obj)
        self._obj_names.append(obj.name)
        self._mesh_names.append(mesh.name)
        return obj

    def test_prefetched_depsgraph_matches_result(self):
        """Pre-fetched depsgraph path must produce identical COM to per-call path."""
        obj_percall = self._make_tri_mesh('b1')
        obj_prefetch = self._make_tri_mesh('b2')
        bpy.context.view_layer.update()
        depsgraph = bpy.context.evaluated_depsgraph_get()

        # Per-call path: function fetches its own depsgraph (current behaviour)
        _set_origin_to_com(obj_percall)

        # Pre-fetched path: caller supplies the depsgraph (the fix)
        _set_origin_to_com(obj_prefetch, depsgraph=depsgraph)

        for idx, (v_pc, v_pf) in enumerate(
            zip(obj_percall.data.vertices, obj_prefetch.data.vertices)
        ):
            for axis in range(3):
                self.assertAlmostEqual(
                    v_pc.co[axis], v_pf.co[axis], places=5,
                    msg=f'vertex {idx}[{axis}]: per-call={v_pc.co[axis]:.6f} vs pre-fetched={v_pf.co[axis]:.6f}',
                )
        for axis in range(3):
            self.assertAlmostEqual(
                obj_percall.location[axis], obj_prefetch.location[axis], places=5,
                msg=f'location[{axis}]: per-call={obj_percall.location[axis]:.6f} vs pre-fetched={obj_prefetch.location[axis]:.6f}',
            )


# -- T-key group toggle: update_names() naming correctness -------------------


class TestGroupToggleNamingCorrectness(unittest.TestCase):
    """Tests for naming correctness in the T-key collider group toggle handler.

    Covers two bugs fixed together:

    Bug 1 — same-formula suffix bump: update_names() did not exclude each
    object's current name from the uniqueness search.  When two groups share
    the same naming formula, unique_name() saw 'collider_001' as taken and
    returned 'collider_002', bumping all suffixes on every toggle even though
    the names were already correct.  Same class of bug fixed for Assign User
    Group and Assign Shape in PR 597 (b2892f1).

    Bug 2 — stale naming cache on group round-trip: _naming_cache was not
    reset when the group changed, so toggling A → B → A restarted numbering
    from the cache value left by the B pass rather than from 001.

    update_names() is driven directly rather than through modal() because
    modal() requires a viewport context (context.space_data) unavailable in
    headless Blender.  Requires the add-on to be registered.
    """

    _N = 5
    _PREFIX = '__test_gtog_'

    @classmethod
    def setUpClass(cls):
        registered_key = _find_registered_addon_key()
        orig = _prim_mod.base_package
        if registered_key is not None and registered_key != orig:
            _prim_mod.base_package = registered_key
            cls._base_package_patched = orig
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
        self._objs = []
        for i in range(self._N):
            mesh = bpy.data.meshes.new(f'{self._PREFIX}mesh_{i}')
            mesh.from_pydata(
                [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)], [], [[0, 1, 2]]
            )
            mesh.update()
            obj = bpy.data.objects.new(f'{self._PREFIX}obj_{i}', mesh)
            bpy.context.collection.objects.link(obj)
            self._objs.append(obj)

    def tearDown(self):
        for obj in list(self._objs):
            _remove_obj(obj)
        self._objs = []

    def _make_fake(self, basename):
        """Build a minimal stand-in for OBJECT_OT_add_bounding_object with
        enough attributes to drive update_names()."""
        if not self._addon_available:
            return None
        colSettings = bpy.context.scene.simple_collider
        group = colSettings.visibility_toggle_user_group_01
        fake = _types.SimpleNamespace(
            new_colliders_list=list(self._objs),
            collision_groups=[group],
            collision_group_idx=0,
            shape='box_shape',
            basename=basename,
            data_suffix='_data',
            _naming_cache={},
        )
        # update_names() calls self.collider_name() and self.set_data_name();
        # bind both onto the fake so the unbound class methods can find them.
        def _collider_name(basename=None, exclude=None):
            if basename is None:
                basename = fake.basename
            user_group = fake.collision_groups[fake.collision_group_idx].identifier
            return _OBJECT_OT_add_bounding_object.class_collider_name(
                fake.shape, user_group, basename=basename, exclude=exclude,
                cache=fake._naming_cache
            )
        fake.collider_name = _collider_name
        fake.set_data_name = _OBJECT_OT_add_bounding_object.set_data_name
        return fake

    def test_single_call_with_fresh_cache_produces_sequential_suffixes(self):
        """Regression guard: one update_names() call with a fresh _naming_cache
        produces sequential suffixes 1 through N.

        Passes before and after the fix.  Verifies the baseline behavior of
        update_names() itself — that starting from an empty cache assigns each
        object the lowest available numeric slot in order.
        """
        if not self._addon_available:
            self.skipTest("simple_collider not registered")
        fake = self._make_fake(self._PREFIX + 'base')
        _OBJECT_OT_add_bounding_object.update_names(fake)

        suffixes = sorted(
            int(obj.name.rsplit('_', 1)[-1])
            for obj in fake.new_colliders_list
            if obj.name.rsplit('_', 1)[-1].isdigit()
        )
        self.assertEqual(suffixes, [1, 2, 3, 4, 5],
                         "Expected sequential suffixes 1–5; a stale or shared cache would shift the sequence upward")

    def test_repeated_toggle_to_same_formula_preserves_names(self):
        """update_names() must not increment suffixes when the target name
        already equals the object's current name.

        If two groups share the same naming formula (e.g. both have an empty
        identifier, or both use the same custom identifier), toggling A → B
        should leave names unchanged.  Without excluding the current name from
        the uniqueness check, unique_name() sees 'collider_001' as taken and
        returns 'collider_002', bumping every object one slot higher on each
        toggle even though the names are already correct.

        This is the same class of bug fixed for Assign User Group and Assign
        Shape in PR 597 (b2892f1).
        """
        if not self._addon_available:
            self.skipTest("simple_collider not registered")
        fake = self._make_fake(self._PREFIX + 'base')

        # First call: establish the correct names (001..00N).
        fake._naming_cache = {}
        _OBJECT_OT_add_bounding_object.update_names(fake)
        names_after_first = [obj.name for obj in fake.new_colliders_list]

        # Second call with fresh cache: simulates toggling to a group whose
        # naming formula produces the same base name (e.g. same identifier).
        # Names must be unchanged — each object already carries the lowest
        # available slot when its own current name is treated as available.
        fake._naming_cache = {}
        _OBJECT_OT_add_bounding_object.update_names(fake)
        names_after_second = [obj.name for obj in fake.new_colliders_list]

        self.assertEqual(
            names_after_second, names_after_first,
            f"update_names() changed names on a same-formula toggle:\n"
            f"  before: {names_after_first}\n"
            f"  after:  {names_after_second}\n"
            "Each object already held the lowest available slot; "
            "unique_name() must exclude the current name from its search."
        )

    def test_repeated_call_preserves_names(self):
        """update_names() must restart numbering from 001 on each call without
        the caller clearing _naming_cache first.

        Simulates a group round-trip (A → B → A): after the first call assigns
        names _001.._N, a second call without an explicit cache clear must
        leave those names unchanged.  Without an internal cache reset,
        update_names() resumes from the count left by the previous pass and
        renames every object to _N+1.._2N even though the correct names are
        already assigned.

        Fails before the fix (which moves _naming_cache = {} to the start of
        update_names()); passes after.
        """
        if not self._addon_available:
            self.skipTest("simple_collider not registered")
        fake = self._make_fake(self._PREFIX + 'base_repeat')

        # First call: establish the correct names (001..N).
        fake._naming_cache = {}
        _OBJECT_OT_add_bounding_object.update_names(fake)
        names_after_first = [obj.name for obj in fake.new_colliders_list]

        # Second call without clearing the cache: simulates the stale state
        # the T-key handler left before the fix.  Names must be unchanged.
        _OBJECT_OT_add_bounding_object.update_names(fake)
        names_after_second = [obj.name for obj in fake.new_colliders_list]

        self.assertEqual(
            names_after_second, names_after_first,
            f"update_names() bumped names on a second call without a manual "
            f"cache clear:\n"
            f"  before: {names_after_first}\n"
            f"  after:  {names_after_second}\n"
            "update_names() must clear _naming_cache at entry so each call "
            "restarts numbering from 001."
        )


class TestCreateCollectionUsesContextScene(unittest.TestCase):
    """Regression test for #552: create_collection must link into
    context.scene, not the global bpy.context.scene (which falls back to
    bpy.data.scenes[0] in headless/background mode).
    """

    def setUp(self):
        self.other_scene = bpy.data.scenes.new('SC_TestOtherScene')
        self.created = None

    def tearDown(self):
        if self.created is not None:
            for scene in bpy.data.scenes:
                if scene.collection.children.get(self.created.name) is self.created:
                    scene.collection.children.unlink(self.created)
            bpy.data.collections.remove(self.created)
        bpy.data.scenes.remove(self.other_scene)

    def test_links_under_context_scene_not_bpy_context_scene(self):
        name = 'SC_TestColliders'
        context_stub = _types.SimpleNamespace(scene=self.other_scene)

        self.created = _OBJECT_OT_add_bounding_object.create_collection(context_stub, name)

        self.assertIs(
            self.other_scene.collection.children.get(name), self.created,
            "collection was not linked under the scene passed via context"
        )
        self.assertIsNot(
            bpy.context.scene.collection.children.get(name), self.created,
            "collection was linked under bpy.context.scene instead of the scene from context"
        )


class TestLocalChildCollectionIgnoresLinked(unittest.TestCase):
    """Regression test for #552: linked (library) collections must be
    ignored when looking up an existing collider collection among a
    parent collection's direct children.
    """

    def test_skips_linked_prefers_local(self):
        linked = _types.SimpleNamespace(name='Colliders', library=object())
        local = _types.SimpleNamespace(name='Colliders', library=None)
        parent = _types.SimpleNamespace(children=[linked, local])
        result = _prim_mod._local_child_collection(parent, 'Colliders')
        self.assertIs(result, local)

    def test_returns_none_when_only_linked_exists(self):
        linked = _types.SimpleNamespace(name='Colliders', library=object())
        parent = _types.SimpleNamespace(children=[linked])
        result = _prim_mod._local_child_collection(parent, 'Colliders')
        self.assertIsNone(result)


class TestCreateCollectionIsScopedPerScene(unittest.TestCase):
    """Regression test for #552 follow-up: different scenes must get their
    own collider collection rather than sharing a single collection linked
    into multiple scenes (which would bleed one scene's colliders into
    another via the outliner).
    """

    def setUp(self):
        self.scene_a = bpy.data.scenes.new('SC_TestSceneA')
        self.scene_b = bpy.data.scenes.new('SC_TestSceneB')
        self.created = []

    def tearDown(self):
        for collection in self.created:
            for scene in (self.scene_a, self.scene_b):
                if any(child is collection for child in scene.collection.children):
                    scene.collection.children.unlink(collection)
            if collection.name in bpy.data.collections:
                bpy.data.collections.remove(collection)
        bpy.data.scenes.remove(self.scene_a)
        bpy.data.scenes.remove(self.scene_b)

    def test_each_scene_gets_its_own_collection(self):
        name = 'SC_TestPerSceneColliders'
        ctx_a = _types.SimpleNamespace(scene=self.scene_a)
        ctx_b = _types.SimpleNamespace(scene=self.scene_b)

        col_a = _OBJECT_OT_add_bounding_object.create_collection(ctx_a, name)
        col_b = _OBJECT_OT_add_bounding_object.create_collection(ctx_b, name)
        self.created.extend([col_a, col_b])

        self.assertIsNot(
            col_a, col_b,
            "both scenes were given the same collection object instead of separate ones"
        )
        self.assertFalse(
            any(child is col_b for child in self.scene_a.collection.children),
            "scene B's collider collection leaked into scene A"
        )
        self.assertFalse(
            any(child is col_a for child in self.scene_b.collection.children),
            "scene A's collider collection leaked into scene B"
        )

        # A second call for the same scene must reuse the same collection,
        # not create a third one.
        col_a_again = _OBJECT_OT_add_bounding_object.create_collection(ctx_a, name)
        self.assertIs(col_a_again, col_a)


class TestCreateCollectionReusesAutoSuffixedName(unittest.TestCase):
    """Regression test: when a local collection with the base name already
    exists elsewhere in the file (e.g. another scene's own collider
    collection - local collection names are unique file-wide, not per
    scene), a new collection gets this addon's own "_NN" disambiguation
    suffix on creation (e.g. "Colliders_01") rather than Blender's default
    ".001" style. Later calls in the same scene must recognize and reuse
    that suffixed collection instead of creating a new one every time -
    otherwise a single collider-generation run produces one throwaway
    collection per object instead of one shared collection for the scene.
    """

    def setUp(self):
        self.other_scene = bpy.data.scenes.new('SC_TestSuffixScene')
        # Occupy the base name elsewhere in the file so a same-named
        # collection created afterward is forced to get a "_NN" suffix.
        self.name_holder = bpy.data.collections.new('SC_TestSuffixColliders')
        self.created = []

    def tearDown(self):
        for collection in self.created:
            if any(child is collection for child in self.other_scene.collection.children):
                self.other_scene.collection.children.unlink(collection)
            if collection.name in bpy.data.collections:
                bpy.data.collections.remove(collection)
        if self.name_holder.name in bpy.data.collections:
            bpy.data.collections.remove(self.name_holder)
        bpy.data.scenes.remove(self.other_scene)

    def test_repeated_calls_reuse_the_suffixed_collection(self):
        name = 'SC_TestSuffixColliders'
        context_stub = _types.SimpleNamespace(scene=self.other_scene)

        col1 = _OBJECT_OT_add_bounding_object.create_collection(context_stub, name)
        self.created.append(col1)
        self.assertEqual(
            col1.name, name + '_01',
            "expected the addon's own '_01' disambiguation suffix, not Blender's default '.001'"
        )

        for _ in range(5):
            col_n = _OBJECT_OT_add_bounding_object.create_collection(context_stub, name)
            self.assertIs(
                col_n, col1,
                "repeated create_collection() calls created a new collection instead of "
                "reusing the auto-suffixed one"
            )

        same_name_children = [c for c in self.other_scene.collection.children if c.name.startswith(name)]
        self.assertEqual(
            len(same_name_children), 1,
            f"expected exactly one collider collection in the scene, found: "
            f"{[c.name for c in same_name_children]}"
        )


if __name__ == '__main__':
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
