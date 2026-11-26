# SPDX-License-Identifier: GPL-2.0-or-later
import os
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1]))
from quota_panel.presentation import duration_label, menu_items, reset_label, summary_label, window_label


class PresentationTests(unittest.TestCase):
    def test_js_cases(self):
        self.assertEqual(duration_label(300), "5 h")
        self.assertEqual(duration_label(10080), "7 d")
        self.assertEqual(duration_label(None), "janela sem duração")
        self.assertEqual(window_label({"durationMinutes": 300, "usedPercent": None}), "5 h · uso indisponível")
        self.assertEqual(window_label({"durationMinutes": 60, "usedPercent": 72}), "1 h · 72% usado")
        self.assertEqual(reset_label(None), "Renovação indisponível")
        self.assertEqual(summary_label({"status": "error"}), "—")
        quota = {"status": "ok", "buckets": [{"id": "codex", "windows": [{"durationMinutes": 300, "usedPercent": 32}]}]}
        self.assertEqual(summary_label(quota), "32%")
        self.assertEqual(summary_label({"status": "ok", "buckets": [{"id": "codex", "windows": [{"durationMinutes": 10080, "usedPercent": 16}, {"durationMinutes": 300, "usedPercent": 4}]}]}), "4%")
        self.assertEqual(summary_label({"status": "ok", "buckets": [{"id": "codex", "windows": [{"durationMinutes": 60, "usedPercent": 32}]}]}), "—")
        self.assertEqual(summary_label({"status": "ok", "buckets": [{"id": "codex", "windows": [{"durationMinutes": 300, "usedPercent": None}, {"durationMinutes": 10080, "usedPercent": 16}]}]}), "—")
        self.assertEqual(summary_label({"status": "ok", "buckets": [{"id": "codex", "windows": [{"durationMinutes": 300, "usedPercent": 0}]}]}), "0%")

    def test_acceptance_fixture_and_menu(self):
        os.environ["TZ"] = "America/Recife"
        if hasattr(__import__("time"), "tzset"): __import__("time").tzset()
        self.assertEqual(reset_label(1795647532), "Renova em 25/11/2026, 19:58")
        quota = {"status": "ok", "ordinaryUsageAllowed": False, "checkedAt": 1795644371,
                 "buckets": [{"id": "codex", "name": "Codex", "windows": [{"durationMinutes": 300, "usedPercent": 100, "resetsAt": 1795647532}]}]}
        texts = [item["text"] for item in menu_items(quota)]
        self.assertIn("Uso incluído indisponível nesta conta", texts)
        self.assertIn("5 h · 100% usado", texts)
        self.assertIn("Atualizado às 19:06", texts)
