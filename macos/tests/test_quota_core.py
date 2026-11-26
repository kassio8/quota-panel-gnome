# SPDX-License-Identifier: GPL-2.0-or-later
import os
import sys
import tempfile
import textwrap
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from quota_panel.quota_core import normalize_rate_limits, query_quota, read_quota


class QuotaCoreTests(unittest.TestCase):
    def server(self, body):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "server.py"
        path.write_text(textwrap.dedent(body), encoding="utf-8")
        return [sys.executable, str(path)]

    def test_normalization_matches_reader(self):
        quota = normalize_rate_limits({"rateLimits": {"limitId": "codex", "primary": {
            "usedPercent": 25, "windowDurationMins": 300, "resetsAt": 1793030000}}}, 10)
        self.assertEqual(quota["buckets"][0]["windows"][0]["usedPercent"], 25)

    def test_reads_in_worker_thread(self):
        command = self.server('''
            import json, sys
            first = json.loads(sys.stdin.readline()); print(json.dumps({"id": first["id"], "result": {}}), flush=True)
            sys.stdin.readline(); second = json.loads(sys.stdin.readline())
            print(json.dumps({"id": second["id"], "result": {"rateLimits": {"primary": {"usedPercent": 1, "windowDurationMins": 300}}}}), flush=True)
        ''')
        result = []
        thread = threading.Thread(target=lambda: result.append(read_quota(command, timeout_seconds=2)))
        thread.start(); thread.join(3)
        self.assertFalse(thread.is_alive()); self.assertEqual(result[0]["status"], "ok")

    def test_timeout_kills_child(self):
        with tempfile.TemporaryDirectory() as directory:
            pid_file = Path(directory) / "pid"
            command = self.server(f'''import os, time
from pathlib import Path
Path({str(pid_file)!r}).write_text(str(os.getpid()))
time.sleep(60)
''')
            with self.assertRaises(TimeoutError): read_quota(command, timeout_seconds=.1)
            self.assertFalse(Path(f"/proc/{pid_file.read_text()}").exists()) if os.path.isdir("/proc") else None

    def test_rpc_auth_is_error(self):
        command = self.server('''
            import json, sys
            first = json.loads(sys.stdin.readline()); print(json.dumps({"id": first["id"], "result": {}}), flush=True)
            sys.stdin.readline(); second = json.loads(sys.stdin.readline())
            print(json.dumps({"id": second["id"], "error": {"message": "authentication required"}}), flush=True)
        ''')
        with self.assertRaisesRegex(RuntimeError, "authentication required"):
            read_quota(command, timeout_seconds=2)
        self.assertEqual(query_quota(None)["status"], "error")

