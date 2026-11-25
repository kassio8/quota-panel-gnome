"""Exercise the real installer in temporary XDG directories."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "org.gnome.shell.extensions.codex-quota"


class InstallationTests(unittest.TestCase):
    def test_installs_preferences_assets_and_preserves_saved_appearance(self):
        with tempfile.TemporaryDirectory(prefix="codex-quota-install-") as temp:
            root = Path(temp)
            binaries = root / "bin"
            binaries.mkdir()
            for name, body in {
                "codex": "exit 99\n",
                "gnome-shell": "echo 'GNOME Shell 46.0'\n",
                "gnome-extensions": '[ "$1" = enable ] && [ "$2" = codex-quota@kassio8 ]\n',
            }.items():
                executable = binaries / name
                executable.write_text("#!/bin/sh\n" + body)
                executable.chmod(0o755)
            environment = dict(
                os.environ,
                PATH=str(binaries) + os.pathsep + os.environ["PATH"],
                XDG_DATA_HOME=str(root / "share"),
                XDG_CONFIG_HOME=str(root / "config"),
                GSETTINGS_BACKEND="keyfile",
            )
            target = root / "share/gnome-shell/extensions/codex-quota@kassio8"

            def run(*command):
                return subprocess.run(
                    command, cwd=ROOT, env=environment, text=True,
                    capture_output=True, check=True, timeout=10,
                ).stdout.strip()

            output = run("sh", "install.sh")
            self.assertIn("Configurações…", output)
            for name in (
                "extension.js", "presentation.js", "appearance.js", "refresh.js", "prefs.js",
                "metadata.json", "reader.js", "quota.js", "preferences-ui.js", "LICENSE",
                "quota-panel-color.svg", "quota-panel-symbolic.svg", "quota-panel-terminal-symbolic.svg",
                f"schemas/{SCHEMA}.gschema.xml",
            ):
                self.assertEqual((target / name).read_bytes(), (ROOT / name).read_bytes(), name)
            self.assertTrue((target / "schemas/gschemas.compiled").stat().st_size)
            self.assertEqual(json.loads((target / "metadata.json").read_text())["version"], 7)
            self.assertEqual((target / "codex-path.txt").read_text().strip(), str(binaries / "codex"))

            environment["GSETTINGS_SCHEMA_DIR"] = str(target / "schemas")
            self.assertEqual(run("gsettings", "get", SCHEMA, "icon-size"), "16")
            self.assertEqual(run("gsettings", "get", SCHEMA, "logo-style"), "0")
            self.assertEqual(run("gsettings", "get", SCHEMA, "refresh-interval"), "60")
            run("gsettings", "set", SCHEMA, "icon-size", "24")
            run("gsettings", "set", SCHEMA, "logo-style", "1")
            run("gsettings", "set", SCHEMA, "refresh-interval", "30")
            # Reinstall and create new GSettings clients, as happens next session.
            run("sh", "install.sh")
            self.assertEqual(run("gsettings", "get", SCHEMA, "icon-size"), "24")
            self.assertEqual(run("gsettings", "get", SCHEMA, "logo-style"), "1")
            self.assertEqual(run("gsettings", "get", SCHEMA, "refresh-interval"), "30")


if __name__ == "__main__":
    unittest.main()
