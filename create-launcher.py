#!/usr/bin/env python3
"""Create a local GNOME application shortcut for the graphical installer."""
from pathlib import Path
import sys


def desktop_string(value):
    slash = chr(92)
    return str(value).replace(slash, slash * 2).replace(chr(10), slash + "n").replace(
        chr(13), slash + "r")


def exec_argument(value):
    value = str(value).replace("%", "%%")
    for char in (chr(92), '"', "$", chr(96)):
        value = value.replace(char, chr(92) + char)
    return '"' + desktop_string(value) + '"'


def main():
    source = Path(__file__).resolve().parent
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else source / "codex-quota-update.desktop"
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        "Name=Atualizar Quota Panel",
        "Comment=Instala as alterações locais da extensão por uma janela",
        "Exec=/bin/sh " + exec_argument(source / "install-gui.sh"),
        "TryExec=zenity",
        "Icon=" + desktop_string(source / "quota-panel-color.svg"),
        "Terminal=false",
        "Categories=Utility;",
        "StartupNotify=false",
    ]
    target.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")


if __name__ == "__main__":
    main()
