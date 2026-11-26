# SPDX-License-Identifier: GPL-2.0-or-later
import os
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1]))
from quota_panel.locator import child_environment, find_codex


class LocatorTests(unittest.TestCase):
    def test_path_and_explicit_config(self):
        with tempfile.TemporaryDirectory() as d:
            binary = Path(d) / "codex"; binary.write_text("#!/bin/sh\n"); binary.chmod(0o755)
            self.assertEqual(find_codex(environ={"PATH": d}), str(binary))
            self.assertEqual(find_codex(str(binary), environ={"PATH": ""}), str(binary))
            self.assertIsNone(find_codex(str(binary) + "-missing", environ={"PATH": d}))

    def test_child_environment_adds_binary_directory(self):
        env = child_environment("/opt/homebrew/bin/codex", environ={"PATH": "/usr/bin", "TOKEN": "x"})
        self.assertEqual(env["TOKEN"], "x")
        self.assertEqual(env["PATH"].split(os.pathsep)[:2], ["/opt/homebrew/bin", "/usr/bin"])
