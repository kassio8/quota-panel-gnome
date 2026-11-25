"""Exercise the shipped GJS reader with isolated executable RPC servers."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GjsReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.binary = self.root / 'codex with spaces'
        self.pid = self.root / 'pid'
        self.runtime = self.root / 'extension'
        self.runtime.mkdir()
        for name in ['reader.js', 'quota.js']:
            shutil.copyfile(ROOT / name, self.runtime / name)
        self.home = self.root / 'outro usuário'
        self.home.mkdir()
        self.environment = dict(os.environ, HOME=str(self.home), PATH='/nonexistent')

    def server(self, response):
        self.binary.write_text('#!/usr/bin/python3\nimport json, sys, os, time, signal\n'
            f'open({str(self.pid)!r}, "w").write(str(os.getpid()))\n'
            'assert sys.argv[1:] == ["app-server"]\n'
            'first = json.loads(sys.stdin.readline())\n'
            'assert first["method"] == "initialize"\n'
            'print(json.dumps({"id": 1, "result": {}}), flush=True)\n'
            'assert json.loads(sys.stdin.readline())["method"] == "initialized"\n'
            'assert json.loads(sys.stdin.readline())["method"] == "account/rateLimits/read"\n'
            + response)
        self.binary.chmod(0o755)

    def run_reader(self, timeout='1500'):
        return subprocess.run(['gjs', '-m', str(ROOT / 'reader.js'), str(self.binary), timeout],
            capture_output=True, text=True, timeout=5)

    def assert_reaped(self):
        with self.assertRaises(ProcessLookupError):
            os.kill(int(self.pid.read_text()), 0)

    def test_success_notifications_zero_and_all_windows(self):
        payload = {'rateLimits': {'limitId': 'codex', 'primary': {
            'usedPercent': 0, 'windowDurationMins': 300}, 'secondary': {
            'usedPercent': 25, 'windowDurationMins': 10080}}}
        self.server('print(json.dumps({"method":"notification"}), flush=True)\n'
            f'print(json.dumps({{"id":2,"result":{payload!r}}}), flush=True)\ntime.sleep(60)\n')
        result = self.run_reader()
        self.assertEqual(result.returncode, 0, result.stderr)
        quota = json.loads(result.stdout)
        self.assertEqual(quota['status'], 'ok')
        self.assertEqual([w['usedPercent'] for w in quota['buckets'][0]['windows']], [0, 25])
        self.assert_reaped()

    def test_authentication_error(self):
        self.server('print(json.dumps({"id":2,"error":{"message":"authentication required"}}), flush=True)\n')
        result = self.run_reader()
        self.assertEqual(result.returncode, 1)
        self.assertIn('Codex CLI', json.loads(result.stdout)['message'])
        self.assert_reaped()

    def test_timeout_and_malformed_and_oversized(self):
        for body in ['signal.signal(signal.SIGTERM, signal.SIG_IGN)\ntime.sleep(60)\n',
                     'print("invalid json", flush=True)\n',
                     'sys.stdout.write("x" * (1024*1024+1)); sys.stdout.flush(); time.sleep(60)\n']:
            with self.subTest(body=body):
                self.server(body)
                result = self.run_reader('300')
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(json.loads(result.stdout)['status'], 'error')
                self.assert_reaped()

    def test_sigterm_reaps_child(self):
        self.server('time.sleep(60)\n')
        process = subprocess.Popen(['gjs', '-m', str(ROOT / 'reader.js'), str(self.binary)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            for _ in range(150):
                if self.pid.exists():
                    break
                time.sleep(.01)
            self.assertTrue(self.pid.exists())
            process.send_signal(signal.SIGTERM)
            process.communicate(timeout=3)
            self.assert_reaped()
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def test_missing_explicit_binary(self):
        result = self.run_reader()
        self.assertEqual(result.returncode, 1)
        self.assertIn('Codex CLI', json.loads(result.stdout)['message'])

    def test_unicode_response_split_between_utf8_bytes(self):
        payload = {'rateLimitsByLimitId': {'codex': {'limitName': 'Cota português ☕',
            'primary': {'usedPercent': 8, 'windowDurationMins': 300}}}}
        self.server(f'payload = json.dumps({{"id":2,"result":{payload!r}}}, ensure_ascii=False).encode() + b"\\n"\n'
            'split = payload.index("ê".encode()) + 1\n'
            'sys.stdout.buffer.write(payload[:split]); sys.stdout.buffer.flush(); time.sleep(.03)\n'
            'sys.stdout.buffer.write(payload[split:]); sys.stdout.buffer.flush(); time.sleep(60)\n')
        result = self.run_reader()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['buckets'][0]['name'], 'Cota português ☕')
        self.assert_reaped()

    def test_saved_install_path_without_shell_path(self):
        (self.runtime / 'codex-path.txt').write_text(str(self.binary) + '\n')
        self.server('print(json.dumps({"id":2,"result":{"rateLimits":{}}}), flush=True)\n')
        result = subprocess.run(['/usr/bin/gjs', '-m', str(self.runtime / 'reader.js')],
            env=self.environment, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'unavailable')
        self.assert_reaped()

    def test_current_user_installations_without_shell_path(self):
        for relative in ['.local/bin/codex', '.npm-global/bin/codex']:
            with self.subTest(relative=relative):
                self.binary = self.home / relative
                self.binary.parent.mkdir(parents=True)
                self.server('print(json.dumps({"id":2,"result":{"rateLimits":{}}}), flush=True)\n')
                # A copied historical path must not override this user's installation.
                (self.runtime / 'codex-path.txt').write_text('/bin/false\n')
                result = subprocess.run(['/usr/bin/gjs', '-m', str(self.runtime / 'reader.js')],
                    env=self.environment, capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assert_reaped()
                self.binary.unlink()

    def test_path_takes_priority_over_saved_installation(self):
        self.binary = self.root / 'bin/codex'
        self.binary.parent.mkdir()
        self.server('print(json.dumps({"id":2,"result":{"rateLimits":{}}}), flush=True)\n')
        (self.runtime / 'codex-path.txt').write_text('/bin/false\n')
        result = subprocess.run(['/usr/bin/gjs', '-m', str(self.runtime / 'reader.js')],
            env=dict(self.environment, PATH=str(self.binary.parent)),
            capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_reaped()

    def test_explicit_launcher_finds_adjacent_runtime(self):
        launcher = self.root / 'nvm with spaces/bin/codex'
        launcher.parent.mkdir(parents=True)
        launcher.write_text('#!/usr/bin/env node\n')
        launcher.chmod(0o755)
        self.binary = launcher.with_name('node')
        self.server('print(json.dumps({"id":2,"result":{"rateLimits":{}}}), flush=True)\n')
        self.binary.write_text(self.binary.read_text().replace(
            'assert sys.argv[1:] == ["app-server"]',
            f'assert sys.argv[1:] == [{str(launcher)!r}, "app-server"]'))
        result = subprocess.run(['/usr/bin/gjs', '-m', str(self.runtime / 'reader.js'), str(launcher)],
            env=self.environment, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_reaped()

    def test_missing_cli_in_clean_home_returns_actionable_error(self):
        (self.runtime / 'codex-path.txt').write_text('/missing-user/bin/codex\n')
        result = subprocess.run(['/usr/bin/gjs', '-m', str(self.runtime / 'reader.js')],
            env=self.environment, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('configure o caminho', json.loads(result.stdout)['message'])
