# SPDX-License-Identifier: GPL-2.0-or-later
"""Descoberta do executável `codex` no macOS.

Um app iniciado pelo launchd recebe um PATH mínimo (/usr/bin:/bin:...), sem
Homebrew nem as pastas do npm. Esta ordem espelha reader.js, com os locais
típicos do macOS acrescentados:

1. Caminho explícito nas configurações: se for inválido, é erro (sem fallback).
2. PATH do processo.
3. Pastas conhecidas: Homebrew, ~/.local/bin, ~/.npm-global/bin e o NVM.
4. Caminho gravado pelo instalador, só como último recurso.
"""

from __future__ import annotations

import glob
import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple, Union

PathLike = Union[str, "os.PathLike[str]"]

HOMEBREW_DIRECTORIES = ("/opt/homebrew/bin", "/usr/local/bin")
HOME_RELATIVE_DIRECTORIES = (".local/bin", ".npm-global/bin")
DEFAULT_PATH = "/usr/bin:/bin"


def _home(home: Optional[PathLike]) -> Path:
    return Path(home) if home is not None else Path.home()


def _is_executable_file(path: PathLike) -> bool:
    return os.path.isfile(path) and os.access(path, os.X_OK)


def _version_key(directory: str) -> Tuple[int, ...]:
    # .../versions/node/v22.11.0/bin -> (22, 11, 0)
    name = os.path.basename(os.path.dirname(directory))
    return tuple(int(part) for part in re.findall(r"\d+", name)) or (0,)


def nvm_directories(home: Optional[PathLike] = None) -> List[str]:
    pattern = str(_home(home) / ".nvm" / "versions" / "node" / "*" / "bin")
    return sorted(glob.glob(pattern), key=_version_key, reverse=True)


def known_directories(home: Optional[PathLike] = None) -> List[str]:
    base = _home(home)
    directories = list(HOMEBREW_DIRECTORIES)
    directories.extend(str(base / relative) for relative in HOME_RELATIVE_DIRECTORIES)
    directories.extend(nvm_directories(home))
    return directories


def find_codex(
    configured: str = "",
    *,
    environ: Optional[Mapping[str, str]] = None,
    home: Optional[PathLike] = None,
    saved_path_file: Optional[PathLike] = None,
) -> Optional[str]:
    env = os.environ if environ is None else environ
    explicit = (configured or "").strip()
    if explicit:
        if os.path.isabs(explicit) and _is_executable_file(explicit):
            return explicit
        return None

    detected = shutil.which("codex", path=env.get("PATH", ""))
    if detected:
        return detected

    for directory in known_directories(home):
        candidate = os.path.join(directory, "codex")
        if _is_executable_file(candidate):
            return candidate

    if saved_path_file is not None:
        try:
            saved = Path(saved_path_file).read_text(encoding="utf-8").strip()
        except OSError:
            saved = ""
        if saved and os.path.isabs(saved) and _is_executable_file(saved):
            return saved
    return None


def child_environment(
    binary: str,
    *,
    environ: Optional[Mapping[str, str]] = None,
    home: Optional[PathLike] = None,
) -> Dict[str, str]:
    """Ambiente do `codex app-server`.

    A instalação via npm usa `#!/usr/bin/env node`; por isso a pasta do próprio
    executável (onde o NVM e o Homebrew deixam o node) vai na frente do PATH, e
    as pastas do Homebrew entram no fim para os demais casos.
    """
    env = dict(os.environ if environ is None else environ)
    parts = [os.path.dirname(binary)]
    parts.extend((env.get("PATH") or DEFAULT_PATH).split(os.pathsep))
    parts.extend(HOMEBREW_DIRECTORIES)
    unique: List[str] = []
    for part in parts:
        if part and part not in unique:
            unique.append(part)
    env["PATH"] = os.pathsep.join(unique)
    return env
