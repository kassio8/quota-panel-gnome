"""Run async controller tests without claiming to validate GNOME widgets."""
from pathlib import Path
import subprocess
import unittest


class LifecycleTests(unittest.TestCase):
    def test_controller_lifecycle(self):
        result = subprocess.run(
            ['node', '--test', str(Path(__file__).with_suffix('.js'))],
            capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
