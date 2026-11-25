"""Check real distribution archives, legacy module loading and package isolation."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.output = Path(cls.temp.name)
        subprocess.run(['python3', str(ROOT / 'build.py'), '--output', str(cls.output)], check=True,
                       capture_output=True, text=True)

    def test_archives_versions_and_no_local_or_python_runtime_files(self):
        for family, versions in [('legacy', ['42', '43', '44']),
                                 ('modern', [str(i) for i in range(45, 52)])]:
            with self.subTest(family=family):
                with zipfile.ZipFile(self.output / f'quota-panel-{family}.shell-extension.zip') as archive:
                    names = archive.namelist()
                    metadata = json.loads(archive.read('metadata.json'))
                    self.assertEqual(metadata['shell-version'], versions)
                    self.assertEqual(metadata['uuid'], 'codex-quota@kassio8')
                    self.assertIn('LICENSE', names)
                    self.assertIn('reader.js', names)
                    self.assertIn('schemas/gschemas.compiled', names)
                    self.assertFalse(any(n.endswith(('.py', '.desktop')) for n in names))
                    self.assertNotIn('codex-path.txt', names)
                    self.assertNotIn('install.sh', names)
                    for icon in ('quota-panel-color.svg', 'quota-panel-symbolic.svg', 'quota-panel-terminal-symbolic.svg'):
                        self.assertIn(icon, names)
                    for name in names:
                        if name.endswith(('.js', '.json', '.xml')):
                            self.assertNotIn(b'/home/', archive.read(name), name)
                            self.assertNotIn(b'/root/', archive.read(name), name)
                    target = self.output / family
                    archive.extractall(target)
                    subprocess.run(['glib-compile-schemas', '--strict', str(target / 'schemas')], check=True)
                    for file in target.glob('*.js'):
                        subprocess.run(['node', '--check', '--input-type=module' if family == 'modern'
                            or file.name in ('reader.js', 'quota.js') else '--input-type=commonjs'],
                            input=file.read_text(), text=True, capture_output=True, check=True)

    def test_legacy_shared_module_exports_load_in_gjs(self):
        target = self.output / 'legacy-load'
        with zipfile.ZipFile(self.output / 'quota-panel-legacy.shell-extension.zip') as archive:
            archive.extractall(target)
        script = f'''imports.searchPath.unshift({json.dumps(str(target))});
const label = imports.presentation.summaryLabel({{status:'ok',buckets:[{{id:'codex',windows:[{{durationMinutes:300,usedPercent:4}}]}}]}});
if (label !== '4%') throw Error(label);
if (imports.appearance.LOGO_STYLES.length !== 3) throw Error('styles');
if (typeof imports.refresh.watchRefreshInterval !== 'function') throw Error('refresh');
print('legacy modules loaded');
'''
        result = subprocess.run(['gjs', '-c', script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_extracted_archives_work_for_another_user_without_installer(self):
        for family in ['legacy', 'modern']:
            with self.subTest(family=family):
                target = self.output / f'portable-{family}'
                with zipfile.ZipFile(self.output / f'quota-panel-{family}.shell-extension.zip') as archive:
                    archive.extractall(target)
                home = self.output / f'usuário {family}'
                binary = home / '.local/bin/codex'
                binary.parent.mkdir(parents=True)
                binary.write_text('#!/usr/bin/python3\nimport json, sys\n'
                    'assert sys.argv[1:] == ["app-server"]\n'
                    'for line in sys.stdin:\n'
                    '    message = json.loads(line)\n'
                    '    if "id" in message:\n'
                    '        print(json.dumps({"id":message["id"],"result":{"rateLimits":{}}}), flush=True)\n')
                binary.chmod(0o755)
                result = subprocess.run(['/usr/bin/gjs', '-m', str(target / 'reader.js')],
                    env=dict(os.environ, HOME=str(home), PATH='/nonexistent'),
                    capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout)['status'], 'unavailable')

    def test_unsupported_versions_are_rejected(self):
        for version in ['41', '52']:
            result = subprocess.run(['python3', str(ROOT / 'build.py'), '--stage',
                str(self.output / 'unsupported'), '--shell-version', version], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

    def test_archive_can_target_one_shell_version(self):
        for version, family in [('42', 'legacy'), ('46', 'modern')]:
            with self.subTest(version=version):
                output = self.output / f'only-{version}'
                subprocess.run(['python3', str(ROOT / 'build.py'), '--output', str(output),
                                '--shell-version', version], check=True, capture_output=True)
                self.assertEqual([p.name for p in output.glob('*.zip')],
                                 [f'quota-panel-{family}.shell-extension.zip'])
                with zipfile.ZipFile(next(output.glob('*.zip'))) as archive:
                    metadata = json.loads(archive.read('metadata.json'))
                    self.assertEqual(metadata['shell-version'], [version])
                    self.assertNotIn('version', metadata)
                    source = archive.read('extension.js').decode()
                    self.assertEqual('function init(' in source, family == 'legacy')

    def test_stage_selects_loader_for_each_supported_version(self):
        for version in range(42, 52):
            target = self.output / f'stage-{version}'
            subprocess.run(['python3', str(ROOT / 'build.py'), '--stage', str(target),
                            '--shell-version', str(version)], capture_output=True, text=True, check=True)
            source = (target / 'extension.js').read_text()
            self.assertEqual('function init(' in source, version < 45)
            self.assertEqual('export default class' in source, version >= 45)
