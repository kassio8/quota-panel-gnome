# SPDX-License-Identifier: GPL-2.0-or-later
"""LaunchAgent plist generation."""

import plistlib
from pathlib import Path

from . import LABEL


def plist(venv_python: str, log_dir=None) -> dict:
    logs = Path(log_dir) if log_dir is not None else Path.home() / "Library" / "Logs" / "QuotaPanel"
    return {"Label": LABEL, "ProgramArguments": [venv_python, "-m", "quota_panel"],
            "RunAtLoad": True, "KeepAlive": True, "LimitLoadToSessionType": "Aqua",
            "StandardOutPath": str(logs / "stdout.log"), "StandardErrorPath": str(logs / "stderr.log")}


def write_plist(path, venv_python: str, log_dir=None):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(plistlib.dumps(plist(venv_python, log_dir)))
