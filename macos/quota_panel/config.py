# SPDX-License-Identifier: GPL-2.0-or-later
"""Configurações em ~/Library/Application Support/QuotaPanel/config.json.

No GNOME elas ficam no GSettings. No macOS é um JSON simples que a pessoa edita
pelo item "Configurações…" do menu; mudanças valem na próxima consulta, sem
reiniciar. Um arquivo ausente ou inválido nunca derruba o app: cai nos padrões.
"""

from __future__ import annotations

import json
import math
import os
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from . import APP_NAME

MIN_INTERVAL_SECONDS = 30
MAX_INTERVAL_SECONDS = 900
DEFAULT_INTERVAL_SECONDS = 60

DEFAULT_FILE_TEXT = """{
  "_ajuda": "intervalSeconds: de 30 a 900 (padrão 60). codexPath: caminho absoluto do Codex CLI, sem argumentos; deixe vazio para detectar sozinho. Salve o arquivo e a mudança vale na próxima consulta.",
  "intervalSeconds": 60,
  "codexPath": ""
}
"""

PathLike = Union[str, "os.PathLike[str]"]


def config_dir(home: Optional[PathLike] = None) -> Path:
    base = Path(home) if home is not None else Path.home()
    return base / "Library" / "Application Support" / APP_NAME


def config_path(home: Optional[PathLike] = None) -> Path:
    return config_dir(home) / "config.json"


def saved_codex_path_file(home: Optional[PathLike] = None) -> Path:
    """Caminho gravado pelo instalador; só é usado como último recurso."""
    return config_dir(home) / "codex-path.txt"


@dataclass(frozen=True)
class Settings:
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    codex_path: str = ""


def parse_settings(data: object) -> Settings:
    if not isinstance(data, dict):
        return Settings()
    interval = data.get("intervalSeconds")
    if (
        isinstance(interval, bool)
        or not isinstance(interval, (int, float))
        or not math.isfinite(interval)
    ):
        interval = DEFAULT_INTERVAL_SECONDS
    interval = int(min(MAX_INTERVAL_SECONDS, max(MIN_INTERVAL_SECONDS, round(interval))))
    codex_path = data.get("codexPath")
    codex_path = codex_path.strip() if isinstance(codex_path, str) else ""
    return Settings(interval_seconds=interval, codex_path=codex_path)


def load(path: Optional[PathLike] = None) -> Settings:
    target = Path(path) if path is not None else config_path()
    try:
        with open(target, "r", encoding="utf-8") as handle:
            return parse_settings(json.load(handle))
    except FileNotFoundError:
        return Settings()
    except (OSError, ValueError) as error:
        print(f"Quota Panel: configuração ignorada ({error})", file=sys.stderr)
        return Settings()


def ensure_config(path: Optional[PathLike] = None) -> Path:
    """Cria o arquivo com os padrões se ainda não existir. Nunca sobrescreve."""
    target = Path(path) if path is not None else config_path()
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(DEFAULT_FILE_TEXT, encoding="utf-8")
    os.replace(temporary, target)
    return target


_UNSET = object()


class SettingsStore:
    """Relê o arquivo só quando ele muda (uma chamada a stat por consulta)."""

    def __init__(self, path: Optional[PathLike] = None) -> None:
        self._path = Path(path) if path is not None else config_path()
        self._lock = threading.Lock()
        self._stamp: object = _UNSET
        self._settings = Settings()

    def get(self) -> Settings:
        with self._lock:
            try:
                info = os.stat(self._path)
                stamp: object = (info.st_mtime_ns, info.st_size)
            except OSError:
                stamp = None
            if stamp != self._stamp:
                self._settings = load(self._path) if stamp is not None else Settings()
                self._stamp = stamp
            return self._settings
