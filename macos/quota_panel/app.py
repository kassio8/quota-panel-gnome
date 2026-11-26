# SPDX-License-Identifier: GPL-2.0-or-later
"""Minimal rumps application; imports macOS-only modules at runtime."""

import queue
import subprocess
import threading

from .config import SettingsStore, ensure_config, saved_codex_path_file
from .locator import find_codex
from .presentation import menu_items, summary_label
from .quota_core import query_quota


try:
    import rumps
except ImportError:  # Linux test/import path.
    rumps = None


if rumps is not None:
    class QuotaPanel(rumps.App):
        def __init__(self):
            super().__init__("Quota Panel", title="—", quit_button=None)
            self._store = SettingsStore()
            self._results = queue.Queue()
            self._busy = False
            self._render({"status": "unavailable", "message": "Consultando cota…", "buckets": []})
            self._poll_timer = rumps.Timer(self._poll, 0.1)
            self._query_timer = rumps.Timer(self._refresh, self._store.get().interval_seconds)
            self._poll_timer.start()
            self._query_timer.start()
            self._refresh()

        def _refresh(self, _timer=None):
            if self._busy:
                return
            self._busy = True
            settings = self._store.get()
            self._query_timer.interval = settings.interval_seconds
            threading.Thread(target=self._query, args=(settings,), daemon=True).start()

        def _query(self, settings):
            try:
                binary = find_codex(settings.codex_path, saved_path_file=saved_codex_path_file())
                result = query_quota(binary)
            except Exception:
                result = {"status": "error", "message": "Não foi possível ler a cota do Codex", "buckets": []}
            self._results.put(result)

        def _poll(self, _timer=None):
            try:
                quota = self._results.get_nowait()
            except queue.Empty:
                return
            self._busy = False
            self._render(quota)

        def _render(self, quota):
            self.title = summary_label(quota)
            self.menu.clear()
            for item in menu_items(quota):
                if item["type"] == "separator":
                    self.menu.add(None)
                elif item["type"] == "action":
                    callbacks = {"Atualizar agora": self._refresh, "Configurações…": self._open_config,
                                 "Sair": rumps.quit_application}
                    self.menu.add(rumps.MenuItem(item["text"], callbacks[item["text"]]))
                else:
                    self.menu.add(rumps.MenuItem(item["text"]))

        def _open_config(self, _sender=None):
            path = ensure_config()
            subprocess.Popen(["open", "-t", str(path)])


else:
    class QuotaPanel:
        def __init__(self):
            raise RuntimeError("rumps is required on macOS")

def main():
    app = QuotaPanel()
    try:
        from AppKit import NSApplication
        NSApplication.sharedApplication().setActivationPolicy_(1)
    except ImportError:
        pass
    app.run()
    return 0
