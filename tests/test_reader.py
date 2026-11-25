import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from reader import normalize_rate_limits, read_quota  # noqa: E402


class NormalizeRateLimitsTests(unittest.TestCase):
    def test_preserves_all_buckets_without_duplicating_legacy_view(self):
        result = {
            "ordinaryUsageAllowed": True,
            "rateLimits": {
                "limitId": "codex",
                "primary": {"usedPercent": 12, "windowDurationMins": 300, "resetsAt": 1793030000},
            },
            "rateLimitsByLimitId": {
                "codex": {
                    "limitId": "codex",
                    "limitName": None,
                    "primary": {"usedPercent": 12, "windowDurationMins": 300, "resetsAt": 1793030000},
                    "secondary": {"usedPercent": 40, "windowDurationMins": 10080, "resetsAt": 1793600000},
                },
                "codex_other": {
                    "limitId": "codex_other",
                    "limitName": "Outro modelo",
                    "primary": {"usedPercent": 65, "windowDurationMins": 60, "resetsAt": 1793020000},
                },
            },
        }

        quota = normalize_rate_limits(result, checked_at=1793010000)

        self.assertEqual(quota["status"], "ok")
        self.assertEqual(quota["checkedAt"], 1793010000)
        self.assertEqual(quota["ordinaryUsageAllowed"], True)
        self.assertEqual([bucket["id"] for bucket in quota["buckets"]], ["codex", "codex_other"])
        self.assertEqual(len(quota["buckets"][0]["windows"]), 2)
        self.assertEqual(quota["buckets"][1]["name"], "Outro modelo")
        self.assertEqual(quota["buckets"][0]["windows"][0], {
            "durationMinutes": 300,
            "usedPercent": 12,
            "resetsAt": 1793030000,
        })

    def test_uses_legacy_view_when_multi_bucket_view_is_absent(self):
        quota = normalize_rate_limits({
            "rateLimits": {
                "limitId": "codex",
                "primary": {"usedPercent": 7, "windowDurationMins": 10080, "resetsAt": 1793600000},
                "secondary": None,
            },
        }, checked_at=10)

        self.assertEqual(quota["status"], "ok")
        self.assertEqual(len(quota["buckets"]), 1)
        self.assertEqual(quota["buckets"][0]["windows"][0]["durationMinutes"], 10080)

    def test_empty_multi_bucket_view_does_not_fall_back_to_legacy_data(self):
        quota = normalize_rate_limits({
            "rateLimitsByLimitId": {},
            "rateLimits": {
                "limitId": "codex",
                "primary": {"usedPercent": 7, "windowDurationMins": 10080, "resetsAt": 1793600000},
            },
        }, checked_at=10)

        self.assertEqual(quota["status"], "unavailable")
        self.assertEqual(quota["buckets"], [])

    def test_missing_numbers_stay_missing_and_are_not_reported_as_real_usage(self):
        quota = normalize_rate_limits({
            "rateLimits": {
                "limitId": "codex",
                "primary": {"usedPercent": None, "windowDurationMins": 300, "resetsAt": None},
            },
        }, checked_at=10)

        self.assertEqual(quota["status"], "unavailable")
        self.assertEqual(quota["buckets"][0]["windows"][0]["usedPercent"], None)
        self.assertEqual(quota["buckets"][0]["windows"][0]["resetsAt"], None)

    def test_boolean_fields_are_not_treated_as_protocol_numbers(self):
        quota = normalize_rate_limits({
            "rateLimits": {
                "limitId": "codex",
                "primary": {"usedPercent": True, "windowDurationMins": True, "resetsAt": True},
            },
        }, checked_at=10)

        window = quota["buckets"][0]["windows"][0]
        self.assertIsNone(window["usedPercent"])
        self.assertIsNone(window["durationMinutes"])
        self.assertIsNone(window["resetsAt"])


class ReadQuotaTests(unittest.TestCase):
    def _fake_server(self, body):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "server.py"
        path.write_text(textwrap.dedent(body), encoding="utf-8")
        return [sys.executable, str(path)]

    def test_reads_after_handshake_and_ignores_notifications(self):
        command = self._fake_server('''
            import json
            import sys

            first = json.loads(sys.stdin.readline())
            assert first["method"] == "initialize"
            print(json.dumps({"id": first["id"], "result": {}}), flush=True)
            second = json.loads(sys.stdin.readline())
            assert second["method"] == "initialized"
            third = json.loads(sys.stdin.readline())
            assert third["method"] == "account/rateLimits/read"
            print(json.dumps({"method": "account/rateLimits/updated", "params": {}}), flush=True)
            print(json.dumps({"id": third["id"], "result": {
                "rateLimits": {"limitId": "codex", "primary": {
                    "usedPercent": 25, "windowDurationMins": 300, "resetsAt": 1793030000
                }}
            }}), flush=True)
        ''')

        quota = read_quota(command, timeout_seconds=2)

        self.assertEqual(quota["status"], "ok")
        self.assertEqual(quota["buckets"][0]["windows"][0]["usedPercent"], 25)

    def test_timeout_terminates_child(self):
        with tempfile.TemporaryDirectory() as directory:
            pid_file = Path(directory) / "pid"
            command = self._fake_server(f'''
                import json
                import os
                from pathlib import Path
                import sys
                import time

                Path({str(pid_file)!r}).write_text(str(os.getpid()))
                first = json.loads(sys.stdin.readline())
                print(json.dumps({{"id": first["id"], "result": {{}}}}), flush=True)
                sys.stdin.readline()
                sys.stdin.readline()
                time.sleep(60)
            ''')

            with self.assertRaises(TimeoutError):
                read_quota(command, timeout_seconds=0.4)

            pid = int(pid_file.read_text())
            with self.assertRaises(ProcessLookupError):
                import os
                os.kill(pid, 0)

    def test_rpc_error_does_not_masquerade_as_missing_quota(self):
        command = self._fake_server('''
            import json
            import sys

            first = json.loads(sys.stdin.readline())
            print(json.dumps({"id": first["id"], "result": {}}), flush=True)
            sys.stdin.readline()
            third = json.loads(sys.stdin.readline())
            print(json.dumps({"id": third["id"], "error": {
                "code": -32600, "message": "codex account authentication required to read rate limits"
            }}), flush=True)
        ''')

        with self.assertRaisesRegex(RuntimeError, "authentication required"):
            read_quota(command, timeout_seconds=2)

    def test_sigterm_reaps_app_server_before_reader_exits(self):
        with tempfile.TemporaryDirectory() as directory:
            pid_file = Path(directory) / "child-pid"
            server = self._fake_server(f'''
                import json
                import os
                from pathlib import Path
                import sys
                import time

                Path({str(pid_file)!r}).write_text(str(os.getpid()))
                first = json.loads(sys.stdin.readline())
                print(json.dumps({{"id": first["id"], "result": {{}}}}), flush=True)
                sys.stdin.readline()
                sys.stdin.readline()
                time.sleep(60)
            ''')
            worker_code = (
                "import sys; sys.path.insert(0, %r); from reader import read_quota; "
                "read_quota(%r, timeout_seconds=60)" % (str(ROOT), server)
            )
            worker = subprocess.Popen(
                [sys.executable, "-c", worker_code],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            child_pid = None
            try:
                for _ in range(100):
                    if pid_file.exists():
                        child_pid = int(pid_file.read_text())
                        break
                    import time
                    time.sleep(0.01)
                self.assertIsNotNone(child_pid)
                worker.send_signal(signal.SIGTERM)
                worker.wait(timeout=2)
                with self.assertRaises(ProcessLookupError):
                    os.kill(child_pid, 0)
            finally:
                if worker.poll() is None:
                    worker.kill()
                    worker.wait()
                if child_pid is not None:
                    try:
                        os.kill(child_pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass


if __name__ == "__main__":
    unittest.main()
