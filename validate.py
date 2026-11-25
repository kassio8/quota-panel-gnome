#!/usr/bin/env python3
"""Run all automated checks; skipped tests mean validation is incomplete."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent


def main():
    environment = dict(os.environ, GSETTINGS_BACKEND='memory')
    try:
        subprocess.run(['glib-compile-schemas', '--strict', str(ROOT / 'schemas')], check=True)
        for name in ('presentation', 'appearance', 'refresh', 'preferences', 'quota'):
            subprocess.run(['gjs', '-m', str(ROOT / 'tests' / f'test_{name}.js')],
                           env=environment, check=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as error:
        print(f'Validação interrompida: {error}', file=sys.stderr)
        return 1
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful() or result.skipped:
        print('Validação incompleta: há falhas ou testes ignorados.', file=sys.stderr)
        return 1
    print('Testes automatizados aprovados. A validação em sessão GNOME continua obrigatória.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
