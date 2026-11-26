#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
set -eu
[ "$(uname)" = Darwin ] || { echo "macOS only" >&2; exit 1; }

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APP="$HOME/Library/Application Support/QuotaPanel"
VENV="$APP/venv"
PLIST="$HOME/Library/LaunchAgents/io.github.kassio8.quota-panel.plist"
mkdir -p "$APP" "$HOME/Library/Logs/QuotaPanel"
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install rumps==0.4.0
rm -rf "$APP/quota_panel"
cp -R "$ROOT/quota_panel" "$APP/quota_panel"
SITE=$("$VENV/bin/python" -c 'import site; print(site.getsitepackages()[0])')
rm -rf "$SITE/quota_panel"
cp -R "$ROOT/quota_panel" "$SITE/quota_panel"
CODEX=$(command -v codex || true)
if [ -n "$CODEX" ]; then printf '%s\n' "$CODEX" > "$APP/codex-path.txt"; fi
PYTHONPATH="$APP" "$VENV/bin/python" -c 'from quota_panel.config import ensure_config; ensure_config()'
PLIST="$PLIST" PYTHON="$VENV/bin/python" PYTHONPATH="$APP" "$VENV/bin/python" -c \
  'from quota_panel.launchagent import write_plist; import os; write_plist(os.environ["PLIST"], os.environ["PYTHON"])'
launchctl bootout "gui/$(id -u)/io.github.kassio8.quota-panel" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Quota Panel instalado."
