#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
set -eu
[ "$(uname)" = Darwin ] || { echo "macOS only" >&2; exit 1; }
APP="$HOME/Library/Application Support/QuotaPanel"
PLIST="$HOME/Library/LaunchAgents/io.github.kassio8.quota-panel.plist"
launchctl bootout "gui/$(id -u)/io.github.kassio8.quota-panel" 2>/dev/null || true
rm -f "$PLIST"
SITE=$("$APP/venv/bin/python" -c 'import site; print(site.getsitepackages()[0])' 2>/dev/null || true)
rm -rf "$APP/venv" "$APP/quota_panel" "$APP/codex-path.txt"
[ -z "$SITE" ] || rm -rf "$SITE/quota_panel"
echo "Código removido; config.json foi preservado em: $APP/config.json"
