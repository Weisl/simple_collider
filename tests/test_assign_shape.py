"""Integration tests for the Assign Shape operator.

These test the full COLLISION_OT_assign_shape operator with real Blender
objects, addon preferences, and parenting — the same flow a user triggers.

Run with headless Blender::

    blender --background --python tests/test_assign_shape.py
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

# Classes needed for operator testing.
_CollisionAddonPrefs = _addon.preferences.preferences.CollisionAddonPrefs
_COLLISION_OT_assign_shape = _addon.collider_conversion.convert_to_shape.COLLISION_OT_assign_shape

# -- Helpers -----------------------------------------------------------------

_TEST_PREFIXES = ('UBX_MyObj', 'USP_MyObj', 'UCP_MyObj', 'UCX_MyObj', 'MSH_MyObj', 'MyObj', 'WrongName')


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

class TestAssignShape(unittest.TestCase):
    """Integration tests for COLLISION_OT_assign_shape.

    Default addon preferences produce names like ``UBX_<parent>_001``
    (PREFIX mode, box_shape="UBX", separator="_", 3 digits, groups
    enabled with user_group_01="").
    """

    @classmethod
    def setUpClass(cls):
        bpy.utils.register_class(_CollisionAddonPrefs)
        bpy.context.preferences.addons.new().module = _ADDON_NAME
        bpy.utils.register_class(_COLLISION_OT_assign_shape)

    @classmethod
    def tearDownClass(cls):
        bpy.utils.unregister_class(_COLLISION_OT_assign_shape)
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
        if prefs.sphere_shape != 'USP':
            self.skipTest("test assumes sphere_shape='USP'")
        if prefs.collision_digits != 3:
            self.skipTest("test assumes collision_digits=3")
        if not prefs.collider_groups_enabled:
            self.skipTest("test assumes collider_groups_enabled=True")
        if prefs.user_group_01 != '':
            self.skipTest("test assumes user_group_01=''")

    def tearDown(self):
        _remove_test_objects()

    # -- Shape conversion uses lowest available suffix ------------------------

    def test_box_to_sphere_uses_001_when_no_spheres(self):
        """UBX_MyObj_002 -> USP_MyObj_001 when no spheres exist."""
        parent = _add_parent('MyObj')
        collider = _add_collider('UBX_MyObj_002', parent, shape='box_shape')
        _select_only(collider)
        bpy.ops.object.assign_collider_shape(shape_identifier='sphere_shape')
        self.assertEqual(collider.name, 'USP_MyObj_001')

    def test_box_to_sphere_uses_002_when_001_taken(self):
        """UBX_MyObj_002 -> USP_MyObj_002 when USP_MyObj_001 exists."""
        parent = _add_parent('MyObj')
        _add_empty('USP_MyObj_001')
        collider = _add_collider('UBX_MyObj_002', parent, shape='box_shape')
        _select_only(collider)
        bpy.ops.object.assign_collider_shape(shape_identifier='sphere_shape')
        self.assertEqual(collider.name, 'USP_MyObj_002')

    # -- Reassigning same shape preserves name --------------------------------

    def test_reassign_same_shape_preserves_001(self):
        """Reassigning the same shape should not change the name."""
        parent = _add_parent('MyObj')
        collider = _add_collider('UBX_MyObj_001', parent, shape='box_shape')
        _select_only(collider)
        bpy.ops.object.assign_collider_shape(shape_identifier='box_shape')
        self.assertEqual(collider.name, 'UBX_MyObj_001')

    def test_reassign_same_shape_preserves_002_when_001_taken(self):
        """Reassigning same shape with _001 taken should keep _002."""
        parent = _add_parent('MyObj')
        _add_empty('UBX_MyObj_001')
        collider = _add_collider('UBX_MyObj_002', parent, shape='box_shape')
        _select_only(collider)
        bpy.ops.object.assign_collider_shape(shape_identifier='box_shape')
        self.assertEqual(collider.name, 'UBX_MyObj_002')

    # -- Fills gaps -----------------------------------------------------------

    def test_box_to_sphere_fills_gap(self):
        """UBX_MyObj_003 -> USP_MyObj_001 when _001 is free."""
        parent = _add_parent('MyObj')
        collider = _add_collider('UBX_MyObj_003', parent, shape='box_shape')
        _select_only(collider)
        bpy.ops.object.assign_collider_shape(shape_identifier='sphere_shape')
        self.assertEqual(collider.name, 'USP_MyObj_001')


if __name__ == '__main__':
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
