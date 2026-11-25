#!/usr/bin/env python3
"""Build reviewable GNOME 42–44 and 45–51 packages from one source tree.

This is a development tool, never included in extension archives. Declared
versions are test targets; see DISTRIBUTION.md before submitting to the store.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent
FAMILIES = {'legacy': ['42', '43', '44'], 'modern': [str(i) for i in range(45, 52)]}
SHARED_LEGACY = {'presentation.js', 'appearance.js', 'refresh.js', 'preferences-ui.js'}


def legacy_module(source):
    """Convert only the import/export forms used by our shared modules.

    Fail closed when a new import shape needs an explicit adapter.
    """
    source = re.sub(r"^import (\w+) from 'gi://([^'?]+)(?:\?version=[^']+)?';$",
                    r'const \1 = imports.gi.\2;', source, flags=re.M)
    source = source.replace("import {LOGO_STYLES} from './appearance.js';",
        'const {LOGO_STYLES} = imports.misc.extensionUtils.getCurrentExtension().imports.appearance;')
    source = source.replace('export const ', 'var ').replace('export function ', 'function ')
    if re.search(r'^\s*(import|export)\b', source, re.M):
        raise ValueError('Unrecognized legacy import/export; add an explicit adapter')
    return '// Generated from shared source by build.py. Do not edit this copy.\n' + source


def legacy_extension(source):
    replacements = {
        "import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';": '''const ExtensionUtils = imports.misc.extensionUtils;
const Me = ExtensionUtils.getCurrentExtension();
class Extension {
    constructor() {
        this.metadata = Me.metadata;
        this.uuid = Me.uuid;
        this.dir = Me.dir;
        this.path = Me.path;
    }
    getSettings() { return ExtensionUtils.getSettings(); }
    openPreferences() { ExtensionUtils.openPrefs(); }
}''',
        "import * as Main from 'resource:///org/gnome/shell/ui/main.js';": 'const Main = imports.ui.main;',
        "import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';": 'const PanelMenu = imports.ui.panelMenu;',
        "import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';": 'const PopupMenu = imports.ui.popupMenu;',
        "import {resetLabel, summaryLabel, windowLabel} from './presentation.js';":
            'const {resetLabel, summaryLabel, windowLabel} = Me.imports.presentation;',
        "import {watchAppearance} from './appearance.js';": 'const {watchAppearance} = Me.imports.appearance;',
        "import {watchRefreshInterval} from './refresh.js';": 'const {watchRefreshInterval} = Me.imports.refresh;',
        'export default class CodexQuotaExtension extends Extension': 'class CodexQuotaExtension extends Extension',
    }
    for before, after in replacements.items():
        if source.count(before) != 1:
            raise ValueError(f'Extension adapter no longer matches: {before}')
        source = source.replace(before, after)
    return legacy_module(source) + '\nfunction init() { return new CodexQuotaExtension(); }\n'


LEGACY_PREFS = '''// SPDX-License-Identifier: GPL-2.0-or-later
// Generated entry point for GNOME 42–44.
imports.gi.versions.Gtk = '4.0';
imports.gi.versions.Adw = '1';
const ExtensionUtils = imports.misc.extensionUtils;
const Me = ExtensionUtils.getCurrentExtension();
function init() {}
function fillPreferencesWindow(window) {
    Me.imports['preferences-ui'].fillPreferences(window, ExtensionUtils.getSettings());
}
'''


def stage(target, family, versions=None):
    target.mkdir(parents=True, exist_ok=True)
    for name in (ROOT / 'extension-files.txt').read_text().splitlines():
        if not name:
            continue
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    metadata = json.loads((target / 'metadata.json').read_text())
    metadata['shell-version'] = versions or FAMILIES[family]
    if versions is None:
        # extensions.gnome.org assigns its own version number on upload.
        metadata.pop('version', None)
    (target / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    if family == 'legacy':
        for name in SHARED_LEGACY:
            path = target / name
            path.write_text(legacy_module(path.read_text()))
        path = target / 'extension.js'
        path.write_text(legacy_extension(path.read_text()))
        (target / 'prefs.js').write_text(LEGACY_PREFS)
    subprocess.run(['glib-compile-schemas', '--strict', str(target / 'schemas')], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    parser.add_argument('--stage', type=Path)
    parser.add_argument('--shell-version', choices=sum(FAMILIES.values(), []))
    args = parser.parse_args()
    if args.stage:
        if not args.shell_version:
            parser.error('--stage requires --shell-version')
        if args.stage.exists() and any(args.stage.iterdir()):
            parser.error('--stage must be empty to prevent stale package files')
        family = 'legacy' if args.shell_version in FAMILIES['legacy'] else 'modern'
        stage(args.stage, family, [args.shell_version])
        return
    args.output.mkdir(parents=True, exist_ok=True)
    for family, versions in FAMILIES.items():
        if args.shell_version and args.shell_version not in versions:
            continue
        with tempfile.TemporaryDirectory(prefix='codex-quota-build-') as temporary:
            source = Path(temporary)
            stage(source, family)
            if args.shell_version:
                metadata_path = source / 'metadata.json'
                metadata = json.loads(metadata_path.read_text())
                metadata['shell-version'] = [args.shell_version]
                metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
            archive_path = args.output / f'quota-panel-{family}.shell-extension.zip'
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(source.rglob('*')):
                    if path.is_file():
                        archive.write(path, path.relative_to(source))
            print(archive_path)


if __name__ == '__main__':
    main()
