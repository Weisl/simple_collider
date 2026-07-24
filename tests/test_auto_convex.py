"""Unit tests for the Auto Convex executable/path-resolution logic
(auto_Convex.add_bounding_auto_convex / add_bounding_auto_convex_coacd).

Both VHACD_OT_convex_decomposition and COACD_OT_convex_decomposition are
modal operators (like the other Add Bounding Shape operators) that require a
real VIEW_3D context and shell out to a bundled platform executable - so,
following the pattern in test_bounding_voxel.py/test_bounding_sphere.py,
these tests exercise the two @staticmethod path-resolution helpers directly
rather than the operator itself. Those two methods are exactly what decides
whether Auto Convex finds its executable at all, which is the most common
real-world failure mode (missing/blocked/relocated executable) and
previously had no coverage.

Run with headless Blender::

    blender --background --python tests/test_auto_convex.py
"""
import os
import stat
import sys
import tempfile
import unittest

import bpy

# Make the add-on importable as a package.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ADDON_NAME = os.path.basename(_PROJECT_ROOT)
sys.path.insert(0, os.path.dirname(_PROJECT_ROOT))

_addon = __import__(_ADDON_NAME)
_VHACD_OT = _addon.auto_Convex.add_bounding_auto_convex.VHACD_OT_convex_decomposition
_COACD_OT = _addon.auto_Convex.add_bounding_auto_convex_coacd.COACD_OT_convex_decomposition

# Both operator classes define identical overwrite_executable_path/
# set_temp_data_path @staticmethods (VHACD and CoACD share the same
# resolution logic) - parametrize each test over both classes so a
# regression in either backend is caught.
_OPERATOR_CLASSES = (_VHACD_OT, _COACD_OT)


class TestOverwriteExecutablePath(unittest.TestCase):
    """overwrite_executable_path(path) is what lets a user point Auto Convex
    at a custom executable location; it must resolve a real file and
    reject anything that doesn't exist on disk."""

    def test_existing_file_resolves(self):
        with tempfile.NamedTemporaryFile() as tmp:
            for op_cls in _OPERATOR_CLASSES:
                result = op_cls.overwrite_executable_path(tmp.name)
                self.assertEqual(result, bpy.path.abspath(tmp.name))

    def test_missing_file_returns_false(self):
        missing_path = os.path.join(tempfile.gettempdir(), 'simple_collider_test_does_not_exist.exe')
        self.assertFalse(os.path.exists(missing_path))
        for op_cls in _OPERATOR_CLASSES:
            self.assertFalse(op_cls.overwrite_executable_path(missing_path))

    def test_empty_path_returns_false(self):
        for op_cls in _OPERATOR_CLASSES:
            self.assertFalse(op_cls.overwrite_executable_path(''))

    def test_directory_path_returns_false(self):
        # A directory isn't a valid executable, even though it exists.
        with tempfile.TemporaryDirectory() as tmp_dir:
            for op_cls in _OPERATOR_CLASSES:
                self.assertFalse(op_cls.overwrite_executable_path(tmp_dir))


class TestSetTempDataPath(unittest.TestCase):
    """set_temp_data_path(path) resolves where Auto Convex exports/imports
    its intermediate OBJ files; it must fall back to the system temp
    directory rather than fail outright when the configured path is empty,
    doesn't exist, or isn't writable."""

    def test_valid_writable_dir_is_used_as_is(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            for op_cls in _OPERATOR_CLASSES:
                result = op_cls.set_temp_data_path(tmp_dir)
                self.assertEqual(result, os.path.normpath(bpy.path.abspath(tmp_dir)))

    def test_empty_path_falls_back_to_system_temp(self):
        for op_cls in _OPERATOR_CLASSES:
            result = op_cls.set_temp_data_path('')
            self.assertEqual(result, tempfile.gettempdir())

    def test_nonexistent_path_falls_back_to_system_temp(self):
        missing_dir = os.path.join(tempfile.gettempdir(), 'simple_collider_test_missing_dir')
        self.assertFalse(os.path.isdir(missing_dir))
        for op_cls in _OPERATOR_CLASSES:
            result = op_cls.set_temp_data_path(missing_dir)
            self.assertEqual(result, tempfile.gettempdir())

    def test_non_writable_dir_falls_back_to_system_temp(self):
        if os.name == 'nt' or hasattr(os, 'geteuid') and os.geteuid() == 0:
            self.skipTest("permission bits aren't enforced for root or on Windows")

        with tempfile.TemporaryDirectory() as tmp_dir:
            os.chmod(tmp_dir, stat.S_IREAD | stat.S_IEXEC)
            try:
                for op_cls in _OPERATOR_CLASSES:
                    result = op_cls.set_temp_data_path(tmp_dir)
                    self.assertEqual(result, tempfile.gettempdir())
            finally:
                # Restore write permission so TemporaryDirectory can clean up.
                os.chmod(tmp_dir, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)


if __name__ == '__main__':
    # Strip Blender's argv; everything after '--' is forwarded to unittest.
    try:
        idx = sys.argv.index('--')
        sys.argv = [sys.argv[0]] + sys.argv[idx + 1:]
    except ValueError:
        sys.argv = [sys.argv[0]]
    unittest.main()
