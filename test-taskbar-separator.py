#!/usr/bin/env python3
"""
Test suite for gnome-taskbar-separator

Imports directly from taskbar_separator.py — place both files in the same
directory and run:

    python3 test_taskbar_separator.py -v

Uses only stdlib (unittest + unittest.mock). No GNOME desktop required.
Pillow is required (same as the main project).
"""

import ast
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import importlib.util

# Import hyphenated filename via importlib
_spec = importlib.util.spec_from_file_location(
    "taskbar_separator",
    Path(__file__).resolve().parent / "taskbar-separator.py",
)
ts = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ts)


# ---------------------------------------------------------------------------
# Test helper: fake gsettings
# ---------------------------------------------------------------------------

def mock_gsettings(favorites_list):
    """Return a (side_effect, state) pair that simulates gsettings get/set."""
    state = {"favorites": list(favorites_list)}

    def side_effect(cmd, **kwargs):
        if cmd[1] == "get":
            out = str(state["favorites"]).replace('"', "'")
            return subprocess.CompletedProcess(cmd, 0, stdout=out + "\n", stderr="")
        if cmd[1] == "set":
            state["favorites"] = ast.literal_eval(cmd[4])
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="unknown")

    return side_effect, state


# ---------------------------------------------------------------------------
# Base class: redirect module-level paths to a temp directory
# ---------------------------------------------------------------------------

class _TempDirTestCase(unittest.TestCase):
    """Patches ICON_DIR / APPS_DIR / ICON_PATH_* on the imported module."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        base = Path(self._tmpdir)
        self._icon_dir = base / "icons"
        self._apps_dir = base / "applications"
        self._icon_dir.mkdir()
        self._apps_dir.mkdir()

        # Save originals, then patch
        self._originals = {
            "ICON_DIR": ts.ICON_DIR,
            "APPS_DIR": ts.APPS_DIR,
            "ICON_PATH_V": ts.ICON_PATH_V,
            "ICON_PATH_H": ts.ICON_PATH_H,
        }
        ts.ICON_DIR = self._icon_dir
        ts.APPS_DIR = self._apps_dir
        ts.ICON_PATH_V = self._icon_dir / "taskbar-separator.png"
        ts.ICON_PATH_H = self._icon_dir / "taskbar-separator-h.png"

    def tearDown(self):
        # Restore originals
        for attr, val in self._originals.items():
            setattr(ts, attr, val)
        shutil.rmtree(self._tmpdir, ignore_errors=True)


# ===========================================================================
# Tests: get_favorites
# ===========================================================================

class TestGetFavorites(unittest.TestCase):

    def _run_with_stdout(self, stdout, returncode=0):
        with mock.patch("subprocess.run") as m:
            m.return_value = subprocess.CompletedProcess(
                [], returncode, stdout=stdout, stderr=""
            )
            return ts.get_favorites()

    def test_normal_list(self):
        result = self._run_with_stdout("['nautilus.desktop', 'firefox.desktop']\n")
        self.assertEqual(result, ["nautilus.desktop", "firefox.desktop"])

    def test_single_item(self):
        result = self._run_with_stdout("['solo.desktop']\n")
        self.assertEqual(result, ["solo.desktop"])

    def test_empty_output(self):
        self.assertEqual(self._run_with_stdout("\n"), [])

    def test_empty_string(self):
        self.assertEqual(self._run_with_stdout(""), [])

    def test_typed_empty_array_BUG(self):
        # BUG: gsettings can return "@as []" for a typed empty array.
        # The fallback parser doesn't strip the GVariant type prefix,
        # producing ['@as'] instead of [].
        # Fix: raw = re.sub(r'^@\w+\s*', '', raw) before parsing.
        result = self._run_with_stdout("@as []\n")
        self.assertEqual(
            result, ["@as"],
            "If this fails, the @as bug was fixed — update this test!",
        )

    def test_nonzero_returncode(self):
        with mock.patch("subprocess.run") as m:
            m.return_value = subprocess.CompletedProcess(
                [], 1, stdout="", stderr="No such schema"
            )
            self.assertEqual(ts.get_favorites(), [])

    def test_filters_empty_strings(self):
        result = self._run_with_stdout(
            "['nautilus.desktop', '', 'firefox.desktop']\n"
        )
        self.assertNotIn("", result)
        self.assertEqual(len(result), 2)

    def test_fallback_parser_on_malformed_input(self):
        result = self._run_with_stdout("[nautilus.desktop, firefox.desktop]\n")
        self.assertEqual(result, ["nautilus.desktop", "firefox.desktop"])


# ===========================================================================
# Tests: set_favorites
# ===========================================================================

class TestSetFavorites(unittest.TestCase):

    def test_formats_gvariant_correctly(self):
        with mock.patch("subprocess.run") as m:
            m.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
            ts.set_favorites(["a.desktop", "b.desktop"])
            sent = m.call_args[0][0][4]
            self.assertEqual(sent, "['a.desktop', 'b.desktop']")

    def test_empty_list(self):
        with mock.patch("subprocess.run") as m:
            m.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
            ts.set_favorites([])
            sent = m.call_args[0][0][4]
            self.assertEqual(sent, "[]")

    def test_exits_on_failure(self):
        with mock.patch("subprocess.run") as m:
            m.return_value = subprocess.CompletedProcess(
                [], 1, stdout="", stderr="err"
            )
            with self.assertRaises(SystemExit):
                ts.set_favorites(["a.desktop"])


# ===========================================================================
# Tests: next_separator_name
# ===========================================================================

class TestNextSeparatorName(_TempDirTestCase):

    def test_first_separator(self):
        self.assertEqual(ts.next_separator_name(), "taskbar-separator")

    def test_second_after_first(self):
        (ts.APPS_DIR / "taskbar-separator.desktop").touch()
        self.assertEqual(ts.next_separator_name(), "taskbar-separator2")

    def test_gap_uses_max_plus_one(self):
        (ts.APPS_DIR / "taskbar-separator.desktop").touch()
        (ts.APPS_DIR / "taskbar-separator3.desktop").touch()
        self.assertEqual(ts.next_separator_name(), "taskbar-separator4")

    def test_ignores_non_numeric_suffix(self):
        (ts.APPS_DIR / "taskbar-separatorfoo.desktop").touch()
        self.assertEqual(ts.next_separator_name(), "taskbar-separator")

    def test_ignores_unrelated_files(self):
        (ts.APPS_DIR / "firefox.desktop").touch()
        (ts.APPS_DIR / "nautilus.desktop").touch()
        self.assertEqual(ts.next_separator_name(), "taskbar-separator")


# ===========================================================================
# Tests: create_icon
# ===========================================================================

class TestCreateIcon(_TempDirTestCase):

    def test_vertical_icon_created(self):
        path = ts.create_icon(horizontal=False)
        self.assertTrue(path.exists())
        self.assertEqual(path.name, "taskbar-separator.png")

    def test_horizontal_icon_created(self):
        path = ts.create_icon(horizontal=True)
        self.assertTrue(path.exists())
        self.assertEqual(path.name, "taskbar-separator-h.png")

    def test_vertical_and_horizontal_differ(self):
        v = ts.create_icon(horizontal=False)
        h = ts.create_icon(horizontal=True)
        self.assertNotEqual(v, h)
        self.assertNotEqual(v.read_bytes(), h.read_bytes())

    def test_does_not_overwrite_existing(self):
        path = ts.create_icon(horizontal=False)
        original = path.read_bytes()
        ts.create_icon(horizontal=False)
        self.assertEqual(path.read_bytes(), original)

    def test_icon_is_64x64_rgba(self):
        from PIL import Image

        path = ts.create_icon(horizontal=False)
        with Image.open(path) as img:
            self.assertEqual(img.size, (64, 64))
            self.assertEqual(img.mode, "RGBA")

    def test_vertical_center_column_has_alpha(self):
        from PIL import Image

        path = ts.create_icon(horizontal=False)
        with Image.open(path) as img:
            alphas = [img.getpixel((31, y))[3] for y in range(8, 56)]
        self.assertTrue(
            all(a > 0 for a in alphas),
            "Vertical line pixels should all have nonzero alpha",
        )

    def test_horizontal_center_row_has_alpha(self):
        from PIL import Image

        path = ts.create_icon(horizontal=True)
        with Image.open(path) as img:
            alphas = [img.getpixel((x, 31))[3] for x in range(8, 56)]
        self.assertTrue(
            all(a > 0 for a in alphas),
            "Horizontal line pixels should all have nonzero alpha",
        )

    def test_corners_are_transparent(self):
        from PIL import Image

        for horiz in (False, True):
            with self.subTest(horizontal=horiz):
                path = ts.create_icon(horizontal=horiz)
                with Image.open(path) as img:
                    for corner in [(0, 0), (63, 0), (0, 63), (63, 63)]:
                        self.assertEqual(
                            img.getpixel(corner)[3], 0,
                            f"Corner {corner} should be fully transparent",
                        )

    def test_alpha_gradient_peaks_at_center(self):
        from PIL import Image

        path = ts.create_icon(horizontal=False)
        with Image.open(path) as img:
            edge_alpha = img.getpixel((31, 8))[3]
            center_alpha = img.getpixel((31, 32))[3]
        self.assertGreater(center_alpha, edge_alpha)


# ===========================================================================
# Tests: create_desktop_file
# ===========================================================================

class TestCreateDesktopFile(_TempDirTestCase):

    def test_creates_file_and_returns_filename(self):
        result = ts.create_desktop_file("taskbar-separator", ts.ICON_PATH_V)
        self.assertEqual(result, "taskbar-separator.desktop")
        self.assertTrue((ts.APPS_DIR / "taskbar-separator.desktop").exists())

    def test_content_has_required_keys(self):
        ts.create_desktop_file("test-sep", ts.ICON_PATH_V)
        content = (ts.APPS_DIR / "test-sep.desktop").read_text()
        self.assertIn("[Desktop Entry]", content)
        self.assertIn("Type=Application", content)
        self.assertIn("Exec=true", content)
        self.assertIn(f"Icon={ts.ICON_PATH_V}", content)

    def test_horizontal_icon_path_embedded(self):
        ts.create_desktop_file("sep-h", ts.ICON_PATH_H)
        content = (ts.APPS_DIR / "sep-h.desktop").read_text()
        self.assertIn("taskbar-separator-h.png", content)

    def test_vertical_icon_path_embedded(self):
        ts.create_desktop_file("sep-v", ts.ICON_PATH_V)
        content = (ts.APPS_DIR / "sep-v.desktop").read_text()
        self.assertIn("taskbar-separator.png", content)
        self.assertNotIn("taskbar-separator-h.png", content)


# ===========================================================================
# Tests: cmd_add / cmd_remove / cmd_list (high-level commands)
# ===========================================================================

class TestCmdAdd(_TempDirTestCase):

    def test_add_default_vertical(self):
        effect, state = mock_gsettings(["nautilus.desktop"])
        with mock.patch("subprocess.run", side_effect=effect):
            ts.cmd_add([])
        self.assertIn("taskbar-separator.desktop", state["favorites"])
        content = (ts.APPS_DIR / "taskbar-separator.desktop").read_text()
        self.assertNotIn("-h.png", content)

    def test_add_horizontal_long_flag(self):
        effect, state = mock_gsettings(["nautilus.desktop"])
        with mock.patch("subprocess.run", side_effect=effect):
            ts.cmd_add(["--horizontal"])
        content = (ts.APPS_DIR / "taskbar-separator.desktop").read_text()
        self.assertIn("taskbar-separator-h.png", content)

    def test_add_horizontal_short_flag(self):
        effect, state = mock_gsettings(["nautilus.desktop"])
        with mock.patch("subprocess.run", side_effect=effect):
            ts.cmd_add(["-H"])
        content = (ts.APPS_DIR / "taskbar-separator.desktop").read_text()
        self.assertIn("taskbar-separator-h.png", content)

    def test_add_appends_to_end(self):
        effect, state = mock_gsettings(["nautilus.desktop", "firefox.desktop"])
        with mock.patch("subprocess.run", side_effect=effect):
            ts.cmd_add([])
        self.assertEqual(state["favorites"], [
            "nautilus.desktop", "firefox.desktop", "taskbar-separator.desktop",
        ])


class TestCmdRemove(_TempDirTestCase):

    def test_removes_last_separator(self):
        (ts.APPS_DIR / "taskbar-separator.desktop").touch()
        (ts.APPS_DIR / "taskbar-separator2.desktop").touch()
        initial = [
            "nautilus.desktop",
            "taskbar-separator.desktop",
            "firefox.desktop",
            "taskbar-separator2.desktop",
        ]
        effect, state = mock_gsettings(initial)
        with mock.patch("subprocess.run", side_effect=effect):
            ts.cmd_remove([])

        self.assertEqual(state["favorites"], [
            "nautilus.desktop", "taskbar-separator.desktop", "firefox.desktop",
        ])
        self.assertFalse((ts.APPS_DIR / "taskbar-separator2.desktop").exists())
        self.assertTrue((ts.APPS_DIR / "taskbar-separator.desktop").exists())

    def test_noop_when_no_separators(self):
        effect, state = mock_gsettings(["nautilus.desktop"])
        with mock.patch("subprocess.run", side_effect=effect):
            ts.cmd_remove([])  # should not crash
        self.assertEqual(state["favorites"], ["nautilus.desktop"])

    def test_deletes_desktop_file(self):
        (ts.APPS_DIR / "taskbar-separator.desktop").write_text("placeholder")
        effect, _ = mock_gsettings(["taskbar-separator.desktop"])
        with mock.patch("subprocess.run", side_effect=effect):
            ts.cmd_remove([])
        self.assertFalse((ts.APPS_DIR / "taskbar-separator.desktop").exists())


class TestCmdList(_TempDirTestCase):

    def test_list_output_contains_apps(self, ):
        effect, _ = mock_gsettings([
            "nautilus.desktop", "taskbar-separator.desktop", "firefox.desktop",
        ])
        with mock.patch("subprocess.run", side_effect=effect):
            with mock.patch("builtins.print") as mock_print:
                ts.cmd_list([])

        printed = "\n".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("nautilus.desktop", printed)
        self.assertIn("separator", printed)
        self.assertIn("firefox.desktop", printed)


# ===========================================================================
# Tests: integration (multi-step flows)
# ===========================================================================

class TestIntegration(_TempDirTestCase):

    def test_add_three_increments_names(self):
        effect, state = mock_gsettings(["nautilus.desktop"])
        with mock.patch("subprocess.run", side_effect=effect):
            for _ in range(3):
                ts.cmd_add([])
        self.assertEqual(len(state["favorites"]), 4)
        self.assertIn("taskbar-separator.desktop", state["favorites"])
        self.assertIn("taskbar-separator2.desktop", state["favorites"])
        self.assertIn("taskbar-separator3.desktop", state["favorites"])

    def test_full_add_remove_cycle(self):
        """Add 2 separators, remove both, verify clean state."""
        effect, state = mock_gsettings(["nautilus.desktop"])
        with mock.patch("subprocess.run", side_effect=effect):
            ts.cmd_add([])
            ts.cmd_add([])
            self.assertEqual(len(state["favorites"]), 3)

            ts.cmd_remove([])
            ts.cmd_remove([])
        self.assertEqual(state["favorites"], ["nautilus.desktop"])

    def test_mixed_vertical_and_horizontal(self):
        effect, state = mock_gsettings(["nautilus.desktop"])
        with mock.patch("subprocess.run", side_effect=effect):
            ts.cmd_add([])               # vertical
            ts.cmd_add(["--horizontal"])  # horizontal

        self.assertEqual(len(state["favorites"]), 3)
        c1 = (ts.APPS_DIR / "taskbar-separator.desktop").read_text()
        c2 = (ts.APPS_DIR / "taskbar-separator2.desktop").read_text()
        self.assertNotIn("-h.png", c1)
        self.assertIn("taskbar-separator-h.png", c2)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()
