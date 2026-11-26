# SPDX-License-Identifier: GPL-2.0-or-later
"""Pure menu-bar presentation functions."""

from datetime import datetime
from typing import Any


def duration_label(minutes):
    if not isinstance(minutes, int) or isinstance(minutes, bool) or minutes <= 0:
        return "janela sem duração"
    if minutes % 1440 == 0:
        return f"{minutes // 1440} d"
    if minutes % 60 == 0:
        return f"{minutes // 60} h"
    return f"{minutes} min"


def reset_label(timestamp):
    if not isinstance(timestamp, int) or isinstance(timestamp, bool) or timestamp <= 0:
        return "Renovação indisponível"
    try:
        date = datetime.fromtimestamp(timestamp).astimezone()
    except (OverflowError, OSError, ValueError):
        return "Renovação indisponível"
    return f"Renova em {date.strftime('%d/%m/%Y, %H:%M')}"


def window_label(window):
    used = window.get("usedPercent")
    used_text = f"{used}% usado" if isinstance(used, (int, float)) and not isinstance(used, bool) else "uso indisponível"
    return f"{duration_label(window.get('durationMinutes'))} · {used_text}"


def summary_label(quota):
    if quota.get("status") != "ok":
        return "—"
    buckets = quota.get("buckets") or []
    bucket = next((item for item in buckets if item.get("id") == "codex"), buckets[0] if buckets else None)
    session = next((item for item in (bucket or {}).get("windows", []) if item.get("durationMinutes") == 300), None)
    used = (session or {}).get("usedPercent")
    return f"{used}%" if isinstance(used, (int, float)) and not isinstance(used, bool) else "—"


def menu_items(quota) -> list[dict[str, Any]]:
    items = []
    if quota.get("status") == "error":
        items.append({"text": quota.get("message", "Cota indisponível"), "type": "line"})
    else:
        if quota.get("ordinaryUsageAllowed") is False:
            items.append({"text": "Uso incluído indisponível nesta conta", "type": "line"})
        if quota.get("status") == "unavailable":
            items.append({"text": quota.get("message", "Cota indisponível"), "type": "line"})
        for bucket in quota.get("buckets") or []:
            windows = bucket.get("windows")
            if not isinstance(windows, list) or not windows:
                continue
            items.append({"text": bucket.get("name", ""), "type": "separator"})
            for window in windows:
                items.append({"text": window_label(window), "type": "line"})
                items.append({"text": reset_label(window.get("resetsAt")), "type": "line"})
        checked = quota.get("checkedAt")
        if isinstance(checked, int) and not isinstance(checked, bool):
            items.append({"text": "", "type": "separator"})
            items.append({"text": f"Atualizado às {datetime.fromtimestamp(checked).astimezone().strftime('%H:%M')}", "type": "line"})
    items.extend(({"text": "", "type": "separator"}, {"text": "Atualizar agora", "type": "action"}, {"text": "Configurações…", "type": "action"}))
    return items


# JS-compatible names are useful to callers ported from presentation.js.
durationLabel = duration_label
resetLabel = reset_label
windowLabel = window_label
summaryLabel = summary_label
