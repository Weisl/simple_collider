"""Tests for version-dependent UI helpers (Blender 5.3 API additions).

Covers both code paths so the suite verifies backwards compatibility on
every Blender version in the CI matrix:

- ``label_multiline``: native ``UILayout.label_multiline()`` on 5.3+,
  textwrap fallback before that.
- ``call_panel`` / keymap: ``auto_keymap`` is passed to ``wm.call_panel``
  only when the operator supports it (5.3+).

Run with headless Blender::

    blender --background --python tests/test_blender_compat.py -- -v
"""
import os
import sys
import types as _types
import unittest
from unittest import mock

import bpy

# Make the add-on importable as a package.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ADDON_NAME = os.path.basename(_PROJECT_ROOT)
sys.path.insert(0, os.path.dirname(_PROJECT_ROOT))

_addon = __import__(_ADDON_NAME)

_panels = _addon.ui.properties_panels
_keymap = _addon.preferences.keymap

_HAS_NATIVE_MULTILINE = 'label_multiline' in bpy.types.UILayout.bl_rna.functions


# -- Fakes -------------------------------------------------------------------


class _LegacyLayout:
    """Layout without label_multiline (Blender < 5.3)."""

    def __init__(self):
        self.labels = []

    def label(self, text=''):
        self.labels.append(text)


class _ModernLayout(_LegacyLayout):
    """Layout with label_multiline (Blender 5.3+)."""

    def __init__(self):
        super().__init__()
        self.multiline = []

    def label_multiline(self, text=''):
        self.multiline.append(text)


def _context(width):
    return _types.SimpleNamespace(region=_types.SimpleNamespace(width=width))


def _fake_bpy(supports_auto_keymap):
    """A stand-in ``bpy`` whose wm.call_panel records its calls."""
    props = {'name': None, 'keep_open': None}
    if supports_auto_keymap:
        props['auto_keymap'] = None
    op = mock.Mock(return_value={'FINISHED'})
    op.get_rna_type.return_value = _types.SimpleNamespace(properties=props)
    return _types.SimpleNamespace(ops=_types.SimpleNamespace(wm=_types.SimpleNamespace(call_panel=op))), op


_LONG_TEXT = ("Auto Convex (High Precision) is only supported for Windows, "
              "Linux, and macOS ARM64 at this moment.")


# -- label_multiline ---------------------------------------------------------


class TestLabelMultiline(unittest.TestCase):

    def test_native_used_when_available(self):
        layout = _ModernLayout()
        _panels.label_multiline(context=_context(100), text=_LONG_TEXT, parent=layout)
        self.assertEqual(layout.multiline, [_LONG_TEXT])
        self.assertEqual(layout.labels, [], "fallback must not run when native exists")

    def test_native_does_not_need_region(self):
        # The native path wraps itself, so a missing region must not matter.
        layout = _ModernLayout()
        _panels.label_multiline(context=_types.SimpleNamespace(region=None),
                                text=_LONG_TEXT, parent=layout)
        self.assertEqual(layout.multiline, [_LONG_TEXT])

    def test_fallback_wraps_on_older_blender(self):
        layout = _LegacyLayout()
        _panels.label_multiline(context=_context(140), text=_LONG_TEXT, parent=layout)  # 20 chars/line
        self.assertGreater(len(layout.labels), 1)
        self.assertTrue(all(len(line) <= 20 for line in layout.labels))
        self.assertEqual(' '.join(layout.labels), _LONG_TEXT)

    def test_real_uilayout_matches_running_version(self):
        self.assertEqual(_HAS_NATIVE_MULTILINE, bpy.app.version >= (5, 3, 0))


# -- call_panel --------------------------------------------------------------


class TestCallPanel(unittest.TestCase):

    def test_auto_keymap_detection_matches_running_version(self):
        self.assertEqual(_panels.call_panel_supports_auto_keymap(),
                         bpy.app.version >= (5, 3, 0))

    def test_passes_auto_keymap_when_supported(self):
        fake, op = _fake_bpy(supports_auto_keymap=True)
        with mock.patch.object(_panels, 'bpy', fake):
            _panels.call_panel("POPUP_PT_auto_convex")
        op.assert_called_once_with(name="POPUP_PT_auto_convex", auto_keymap=True)

    def test_omits_auto_keymap_when_unsupported(self):
        fake, op = _fake_bpy(supports_auto_keymap=False)
        with mock.patch.object(_panels, 'bpy', fake):
            _panels.call_panel("POPUP_PT_auto_convex")
        op.assert_called_once_with(name="POPUP_PT_auto_convex")


# -- keymap ------------------------------------------------------------------


class TestKeymapAutoKeymap(unittest.TestCase):
    """add_key() must set auto_keymap on call_panel items only where supported,
    and must not fail on versions without it."""

    _PANEL = 'VIEW3D_PT_collision_visibility_panel'

    def setUp(self):
        km = bpy.context.window_manager.keyconfigs.addon
        if km is None:
            self.skipTest("no add-on keyconfig in this Blender session")

    def tearDown(self):
        _keymap.remove_key(bpy.context, 'wm.call_panel', self._PANEL)
        _keymap.remove_key(bpy.context, 'wm.call_menu_pie', 'COLLISION_MT_pie_menu')

    def _find(self, idname, name):
        km = bpy.context.window_manager.keyconfigs.addon.keymaps.get('Window')
        return [k for k in km.keymap_items
                if k.idname == idname and k.properties.name == name]

    def test_call_panel_item(self):
        _keymap.add_key(bpy.context, 'wm.call_panel', 'F19', False, True, False, self._PANEL, True)
        items = self._find('wm.call_panel', self._PANEL)
        self.assertEqual(len(items), 1)
        props = items[0].properties
        if bpy.app.version >= (5, 3, 0):
            self.assertTrue(props.auto_keymap)
        else:
            self.assertFalse(hasattr(props, 'auto_keymap'))

    def test_pie_menu_item_unaffected(self):
        _keymap.add_key(bpy.context, 'wm.call_menu_pie', 'F19', True, True, False,
                        'COLLISION_MT_pie_menu', True)
        items = self._find('wm.call_menu_pie', 'COLLISION_MT_pie_menu')
        self.assertEqual(len(items), 1)
        self.assertFalse(hasattr(items[0].properties, 'auto_keymap'))


if __name__ == '__main__':
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
