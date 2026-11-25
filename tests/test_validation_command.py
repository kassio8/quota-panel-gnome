"""Verify the release check never treats a skipped test as full validation."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ValidationCommandTests(unittest.TestCase):
    def test_success_failure_and_skip_exit_codes(self):
        for body, expected in [('pass', 0), ('self.fail("broken")', 1),
                               ('self.skipTest("display unavailable")', 1)]:
            with self.subTest(body=body), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                shutil.copyfile(ROOT / 'validate.py', root / 'validate.py')
                (root / 'schemas').mkdir()
                tests = root / 'tests'
                tests.mkdir()
                # Minimal inputs isolate the command's exit policy, not product tests.
                for name in ('presentation', 'appearance', 'refresh', 'preferences', 'quota'):
                    (tests / f'test_{name}.js').write_text('// Fixture: successful GJS process.\n')
                (tests / 'test_sample.py').write_text(
                    'import unittest\nclass Sample(unittest.TestCase):\n'
                    f'    def test_sample(self):\n        {body}\n')
                result = subprocess.run(['python3', str(root / 'validate.py')],
                                        capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
