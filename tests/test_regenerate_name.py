"""Integration tests for the Regenerate Name operator.

These test the full OBJECT_OT_regenerate_name operator with real Blender
objects, addon preferences, and parenting — the same flow a user triggers.

Run with headless Blender::

    blender --background --python tests/test_regenerate_name.py
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

# Classes needed for operator testing.  We register only the preferences and
# the operator itself — the full addon register() has UI side-effects that
# require the extension system.
_CollisionAddonPrefs = _addon.preferences.preferences.CollisionAddonPrefs
_OBJECT_OT_regenerate_name = _addon.collider_conversion.regenerate_name.OBJECT_OT_regenerate_name

# -- Helpers -----------------------------------------------------------------

_TEST_PREFIXES = ('UBX_MyObj', 'MyObj', 'WrongName')


def _add_parent(name):
    """Create a non-collider parent object."""
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    return obj


def _add_collider(name, parent, shape='box_shape', group='USER_01'):
    """Create a mesh object configured as a collider."""
    mesh = bpy.data.meshes.new(name + '_data')
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj['isCollider'] = True
    obj['collider_shape'] = shape
    obj['collider_group'] = group
    obj.parent = parent
    return obj


def _add_empty(name):
    """Create an empty object to occupy a name slot."""
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    return obj


def _select_only(*objs):
    """Deselect everything, then select and activate the given objects."""
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


def _remove_test_objects():
    """Remove every object whose name starts with a test prefix."""
    for obj in list(bpy.data.objects):
        if obj.name.startswith(_TEST_PREFIXES):
            data = obj.data
            bpy.data.objects.remove(obj)
            if isinstance(data, bpy.types.Mesh):
                bpy.data.meshes.remove(data)


# -- Tests -------------------------------------------------------------------

class TestRegenerateName(unittest.TestCase):
    """Integration tests for OBJECT_OT_regenerate_name.

    Default addon preferences produce names like ``UBX_<parent>_001``
    (PREFIX mode, box_shape="UBX", separator="_", 3 digits, groups
    enabled with user_group_01="").
    """

    @classmethod
    def setUpClass(cls):
        bpy.utils.register_class(_CollisionAddonPrefs)
        # Create an addon entry so the operator can look up preferences via
        # ``context.preferences.addons[base_package].preferences``.
        bpy.context.preferences.addons.new().module = _ADDON_NAME
        bpy.utils.register_class(_OBJECT_OT_regenerate_name)

    @classmethod
    def tearDownClass(cls):
        bpy.utils.unregister_class(_OBJECT_OT_regenerate_name)
        addons = bpy.context.preferences.addons
        entry = addons.get(_ADDON_NAME)
        if entry is not None:
            addons.remove(entry)
        bpy.utils.unregister_class(_CollisionAddonPrefs)

    def setUp(self):
        _remove_test_objects()
        prefs = bpy.context.preferences.addons[_ADDON_NAME].preferences
        if prefs.naming_position != 'PREFIX':
            self.skipTest("test assumes naming_position='PREFIX'")
        if prefs.separator != '_':
            self.skipTest("test assumes separator='_'")
        if prefs.box_shape != 'UBX':
            self.skipTest("test assumes box_shape='UBX'")
        if prefs.collision_digits != 3:
            self.skipTest("test assumes collision_digits=3")
        if not prefs.collider_groups_enabled:
            self.skipTest("test assumes collider_groups_enabled=True")
        if prefs.user_group_01 != '':
            self.skipTest("test assumes user_group_01=''")

    def tearDown(self):
        _remove_test_objects()

    # -- Basic renaming (pass before and after the fix) ----------------------

    def test_renames_wrong_name_001_taken(self):
        """Wrong name, _001 slot taken -> renamed to _002."""
        parent = _add_parent('MyObj')
        _add_empty('UBX_MyObj_001')
        collider = _add_collider('WrongName', parent)
        _select_only(collider)
        result = bpy.ops.object.regenerate_name()
        self.assertEqual(collider.name, 'UBX_MyObj_002')
        self.assertEqual(result, {'FINISHED'})

    def test_renames_wrong_name_002_taken_001_free(self):
        """Wrong name, _002 taken but _001 free -> renamed to _001."""
        parent = _add_parent('MyObj')
        _add_empty('UBX_MyObj_002')
        collider = _add_collider('WrongName', parent)
        _select_only(collider)
        result = bpy.ops.object.regenerate_name()
        self.assertEqual(collider.name, 'UBX_MyObj_001')
        self.assertEqual(result, {'FINISHED'})

    def test_renames_wrong_name_no_others(self):
        """Wrong name, no conforming objects -> renamed to _001."""
        parent = _add_parent('MyObj')
        collider = _add_collider('WrongName', parent)
        _select_only(collider)
        result = bpy.ops.object.regenerate_name()
        self.assertEqual(collider.name, 'UBX_MyObj_001')
        self.assertEqual(result, {'FINISHED'})

    def test_fills_gap_at_001(self):
        """Collider is _002, no _001 exists -> renamed to _001."""
        parent = _add_parent('MyObj')
        collider = _add_collider('UBX_MyObj_002', parent)
        _select_only(collider)
        result = bpy.ops.object.regenerate_name()
        self.assertEqual(collider.name, 'UBX_MyObj_001')
        self.assertEqual(result, {'FINISHED'})

    # -- Keep-your-name cases (fail before the fix, pass after) --------------

    def test_keeps_001_when_only_collider(self):
        """Collider already _001, only one -> should keep _001."""
        parent = _add_parent('MyObj')
        collider = _add_collider('UBX_MyObj_001', parent)
        _select_only(collider)
        result = bpy.ops.object.regenerate_name()
        self.assertEqual(collider.name, 'UBX_MyObj_001')
        self.assertEqual(result, {'CANCELLED'})

    def test_keeps_002_when_001_taken(self):
        """Collider is _002, another object has _001 -> should keep _002."""
        parent = _add_parent('MyObj')
        _add_empty('UBX_MyObj_001')
        collider = _add_collider('UBX_MyObj_002', parent)
        _select_only(collider)
        result = bpy.ops.object.regenerate_name()
        self.assertEqual(collider.name, 'UBX_MyObj_002')
        self.assertEqual(result, {'CANCELLED'})

    def test_keeps_01_two_digit(self):
        """2-digit: collider already _01, only one -> should keep _01."""
        prefs = bpy.context.preferences.addons[_ADDON_NAME].preferences
        old_digits = prefs.collision_digits
        prefs.collision_digits = 2
        try:
            parent = _add_parent('MyObj')
            collider = _add_collider('UBX_MyObj_01', parent)
            _select_only(collider)
            result = bpy.ops.object.regenerate_name()
            self.assertEqual(collider.name, 'UBX_MyObj_01')
            self.assertEqual(result, {'CANCELLED'})
        finally:
            prefs.collision_digits = old_digits

    def test_keeps_001_when_002_taken(self):
        """Collider is _001, another object has _002 -> should keep _001."""
        parent = _add_parent('MyObj')
        collider = _add_collider('UBX_MyObj_001', parent)
        _add_empty('UBX_MyObj_002')
        _select_only(collider)
        result = bpy.ops.object.regenerate_name()
        self.assertEqual(collider.name, 'UBX_MyObj_001')
        self.assertEqual(result, {'CANCELLED'})


if __name__ == '__main__':
    # Strip Blender's argv; everything after '--' is forwarded to unittest.
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
