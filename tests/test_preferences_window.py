"""Construct both preference entry points with real GTK widgets on Broadway.

This tests installed GTK/Adwaita only, not an actual GNOME 42 desktop.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('gtk4-broadwayd'), 'GTK Broadway backend unavailable')
class PreferenceWindowTests(unittest.TestCase):
    def test_modern_and_legacy_widgets_construct_and_bind(self):
        with tempfile.TemporaryDirectory(prefix='quota-preferences-') as temporary:
            folder = Path(temporary)
            environment = dict(os.environ, XDG_RUNTIME_DIR=temporary, GDK_BACKEND='broadway',
                BROADWAY_DISPLAY=':9', GSETTINGS_BACKEND='memory', GTK_A11Y='none')
            server = subprocess.Popen(['gtk4-broadwayd', '--unixsocket', str(folder / 'http.socket'), ':9'],
                env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            try:
                for _ in range(100):
                    if list(folder.glob('*broadway*')) or server.poll() is not None:
                        break
                    time.sleep(.01)
                if server.poll() is not None:
                    self.skipTest('Broadway unavailable in this sandbox: ' + server.stderr.read())
                common = '''
const source = Gio.SettingsSchemaSource.new_from_directory(SCHEMAS, Gio.SettingsSchemaSource.get_default(), false);
const settings = new Gio.Settings({settings_schema: source.lookup('org.gnome.shell.extensions.codex-quota', false)});
Adw.init();
const window = new Adw.PreferencesWindow();
FILL
function descendants(widget) {
    const items = [widget];
    for (let child = widget.get_first_child(); child; child = child.get_next_sibling())
        items.push(...descendants(child));
    return items;
}
const widgets = descendants(window);
const spins = widgets.filter(widget => widget instanceof Gtk.SpinButton);
if (spins.length !== 2) throw Error('Expected size and refresh controls');
spins[0].value = 22;
spins[1].value = 30;
if (settings.get_int('icon-size') !== 22 || settings.get_int('refresh-interval') !== 30)
    throw Error('Spin controls must persist');
const path = widgets.find(widget => widget instanceof Gtk.Entry && widget.placeholder_text === '/caminho/para/codex');
if (!path) throw Error('Executable path entry missing');
path.text = '/tmp/codex with spaces';
if (settings.get_string('codex-path') !== path.text) throw Error('Path must persist');
window.present();
window.destroy();
print('preferences window constructed and bound');
'''
                modern = "import Adw from 'gi://Adw?version=1';\nimport Gtk from 'gi://Gtk?version=4.0';\nimport Gio from 'gi://Gio';\n"
                modern += f"import {{fillPreferences}} from {json.dumps((ROOT / 'preferences-ui.js').as_uri())};\n"
                modern += common.replace('SCHEMAS', json.dumps(str(ROOT / 'schemas'))).replace('FILL', 'fillPreferences(window, settings);')
                script = folder / 'modern.js'
                script.write_text(modern)
                result = subprocess.run(['gjs', '-m', str(script)], env=environment,
                    capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

                stage = folder / 'legacy'
                subprocess.run(['python3', str(ROOT / 'build.py'), '--stage', str(stage),
                    '--shell-version', '42'], check=True, capture_output=True)
                (stage / 'misc').mkdir()
                (stage / 'misc/extensionUtils.js').write_text('''
function getCurrentExtension() { return {imports}; }
function getSettings() { return globalThis.testSettings; }
''')
                legacy = "imports.gi.versions.Gtk = '4.0'; imports.gi.versions.Adw = '1';\nconst {Adw, Gtk, Gio} = imports.gi;\n"
                legacy += f'imports.searchPath.unshift({json.dumps(str(stage))});\n'
                legacy += common.replace('SCHEMAS', json.dumps(str(stage / 'schemas'))).replace('FILL',
                    'globalThis.testSettings = settings; imports.prefs.fillPreferencesWindow(window);')
                script = folder / 'legacy.js'
                script.write_text(legacy)
                result = subprocess.run(['gjs', str(script)], env=environment,
                    capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            finally:
                server.terminate()
                server.communicate(timeout=3)
