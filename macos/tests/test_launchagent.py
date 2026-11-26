# SPDX-License-Identifier: GPL-2.0-or-later
import plistlib
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1]))
from quota_panel.launchagent import plist, write_plist

class LaunchAgentTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "agent.plist"; write_plist(path, "/tmp/venv/bin/python", Path(d) / "logs", Path(d) / "app")
            data = plistlib.loads(path.read_bytes())
            self.assertEqual(data, plist("/tmp/venv/bin/python", Path(d) / "logs", Path(d) / "app"))
            self.assertEqual(data["ProgramArguments"], ["/tmp/venv/bin/python", "-m", "quota_panel"])
            self.assertEqual(data["KeepAlive"], {"SuccessfulExit": False})
            self.assertEqual(data["EnvironmentVariables"], {"PYTHONPATH": str(Path(d) / "app")})
