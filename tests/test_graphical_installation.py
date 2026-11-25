"""Run the graphical install workflow with isolated paths and recorded dialogs."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class GraphicalInstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="codex-quota-gui-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.binaries = self.root / "bin"
        self.binaries.mkdir()
        self.dialogs = self.root / "dialogs.jsonl"
        self.environment = dict(
            os.environ, PATH=str(self.binaries) + ":/usr/bin:/bin",
            XDG_DATA_HOME=str(self.root / "share"),
            XDG_CONFIG_HOME=str(self.root / "config"),
            CODEX_QUOTA_TEST_DIALOGS=str(self.dialogs),
        )
        self.executable("gnome-extensions", 'exit 0\n')
        self.executable("gnome-shell", 'echo "GNOME Shell 46.0"\n')
        self.executable("codex", 'exit 99\n')
        zenity = self.binaries / "zenity"
        zenity.write_text(
            '#!/usr/bin/python3\nimport json, os, sys\n'
            'with open(os.environ["CODEX_QUOTA_TEST_DIALOGS"], "a") as stream:\n'
            '    stream.write(json.dumps(sys.argv[1:]) + "\\n")\n'
        )
        zenity.chmod(0o755)

    def executable(self, name, body):
        target = self.binaries / name
        target.write_text("#!/bin/sh\n" + body)
        target.chmod(0o755)
        return target

    def run_gui(self):
        return subprocess.run(
            ["sh", str(ROOT / "install-gui.sh")], env=self.environment,
            text=True, capture_output=True, timeout=10,
        )

    def messages(self):
        return [json.loads(line) for line in self.dialogs.read_text().splitlines()]

    def test_click_installs_registers_launcher_and_recognizes_no_code_change(self):
        first = self.run_gui()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("--info", self.messages()[-1])
        self.assertIn("saia da sessão", " ".join(self.messages()[-1]))
        launcher = self.root / "share/applications/codex-quota-update.desktop"
        self.assertTrue(launcher.is_file())
        text = launcher.read_text()
        self.assertIn("Terminal=false", text)
        self.assertIn("install-gui.sh", text)
        self.assertIn("Atualizar Quota Panel", text)
        subprocess.run(["desktop-file-validate", str(launcher)], check=True, capture_output=True)
        second = self.run_gui()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertNotIn("saia da sessão", " ".join(self.messages()[-1]))

    def test_codex_saved_path_works_without_codex_on_desktop_path(self):
        self.assertEqual(self.run_gui().returncode, 0)
        original = self.binaries / "codex"
        saved = self.root / "codex fora do PATH"
        shutil.move(original, saved)
        path_file = self.root / "share/gnome-shell/extensions/codex-quota@kassio8/codex-path.txt"
        path_file.write_text(str(saved) + "\n")
        result = self.run_gui()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(path_file.read_text().strip(), str(saved))

    def test_legacy_install_and_repeat_use_generated_files(self):
        self.executable("gnome-shell", 'echo "GNOME Shell 42.9"\n')
        first = self.run_gui()
        self.assertEqual(first.returncode, 0, first.stderr)
        target = self.root / "share/gnome-shell/extensions/codex-quota@kassio8"
        self.assertIn('function init()', (target / 'extension.js').read_text())
        self.assertEqual(json.loads((target / 'metadata.json').read_text())['shell-version'], ['42'])
        self.assertEqual(self.run_gui().returncode, 0)
        self.assertNotIn("saia da sessão", " ".join(self.messages()[-1]))

    def test_failed_install_shows_error_instead_of_success(self):
        self.executable("glib-compile-schemas", 'printf "%s\\n" "Falha no schema" >&2\nexit 42\n')
        result = self.run_gui()
        self.assertNotEqual(result.returncode, 0)
        messages = self.messages()
        self.assertIn("--error", messages[-1])
        self.assertIn("Falha no schema", " ".join(messages[-1]))
        self.assertFalse(any("--info" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
