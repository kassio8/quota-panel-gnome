# SPDX-License-Identifier: GPL-2.0-or-later
import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1]))
from quota_panel.config import Settings, load, parse_settings

class ConfigTests(unittest.TestCase):
    def test_invalid_missing_range_and_boolean(self):
        self.assertEqual(parse_settings(None), Settings())
        self.assertEqual(parse_settings({"intervalSeconds": 1}).interval_seconds, 30)
        self.assertEqual(parse_settings({"intervalSeconds": 9999}).interval_seconds, 900)
        self.assertEqual(parse_settings({"intervalSeconds": True}).interval_seconds, 60)
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(load(Path(d) / "missing"), Settings())
            p = Path(d) / "bad"; p.write_text("{")
            self.assertEqual(load(p), Settings())
