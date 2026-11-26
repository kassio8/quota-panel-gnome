# SPDX-License-Identifier: GPL-2.0-or-later
"""Codex app-server reader for the macOS menu-bar app."""

from __future__ import annotations

import json
import os
import selectors
import subprocess
import time
from typing import Mapping, Optional, Sequence

from .locator import child_environment

MAX_RESPONSE_BYTES = 1024 * 1024


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def normalize_rate_limits(result, checked_at):
    if not isinstance(result, dict):
        raise ValueError("Invalid rate limit response")
    multi = result.get("rateLimitsByLimitId")
    if isinstance(multi, dict):
        snapshots = list(multi.items())
    else:
        legacy = result.get("rateLimits")
        snapshots = [(legacy.get("limitId") or "codex", legacy)] if isinstance(legacy, dict) else []
    buckets = []
    for bucket_id, snapshot in snapshots:
        if not isinstance(snapshot, dict):
            continue
        windows = []
        for slot in ("primary", "secondary"):
            window = snapshot.get(slot)
            if not isinstance(window, dict):
                continue
            duration = window.get("windowDurationMins")
            used = window.get("usedPercent")
            resets = window.get("resetsAt")
            windows.append({
                "durationMinutes": duration if isinstance(duration, int) and not isinstance(duration, bool) and duration > 0 else None,
                "usedPercent": used if _number(used) and 0 <= used <= 100 else None,
                "resetsAt": resets if isinstance(resets, int) and not isinstance(resets, bool) and resets > 0 else None,
            })
        if not windows:
            continue
        windows.sort(key=lambda entry: entry["durationMinutes"] or float("inf"))
        name = snapshot.get("limitName")
        if not isinstance(name, str) or not name.strip():
            name = "Codex" if bucket_id == "codex" else str(bucket_id)
        buckets.append({"id": str(bucket_id), "name": name, "windows": windows})
    buckets.sort(key=lambda entry: (entry["id"] != "codex", entry["name"].lower()))
    has_usage = any(window["usedPercent"] is not None for bucket in buckets for window in bucket["windows"])
    quota = {
        "status": "ok" if has_usage else "unavailable",
        "checkedAt": checked_at,
        "ordinaryUsageAllowed": result.get("ordinaryUsageAllowed") if isinstance(result.get("ordinaryUsageAllowed"), bool) else None,
        "buckets": buckets,
    }
    if not has_usage:
        quota["message"] = "O Codex não informou percentuais de cota"
    return quota


def _send(process, message):
    process.stdin.write(json.dumps(message, separators=(",", ":")).encode() + b"\n")
    process.stdin.flush()


def _response(process, request_id, deadline, pending):
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        while True:
            if b"\n" in pending:
                line, pending = pending.split(b"\n", 1)
                if not line:
                    continue
                message = json.loads(line)
                if not isinstance(message, dict) or message.get("id") != request_id:
                    continue
                if "error" in message:
                    error = message["error"]
                    raise RuntimeError(error.get("message", "RPC error") if isinstance(error, dict) else "RPC error")
                if "result" not in message:
                    raise ValueError("Codex response has no result")
                return message["result"], pending
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                raise TimeoutError("Codex did not answer in time")
            chunk = os.read(process.stdout.fileno(), 65536)
            if not chunk:
                raise RuntimeError("Codex app server closed the connection")
            pending += chunk
            if len(pending) > MAX_RESPONSE_BYTES:
                raise ValueError("Codex response is too large")


def read_quota(command: Sequence[str], env: Optional[Mapping[str, str]] = None, timeout_seconds=15):
    process = None
    try:
        process = subprocess.Popen(command, env=dict(env) if env is not None else None,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + timeout_seconds
        _send(process, {"id": 1, "method": "initialize", "params": {"clientInfo": {
            "name": "codex_macos_quota", "title": "Codex macOS Quota", "version": "0.1.0"}}})
        _, pending = _response(process, 1, deadline, b"")
        _send(process, {"method": "initialized", "params": {}})
        _send(process, {"id": 2, "method": "account/rateLimits/read"})
        result, _ = _response(process, 2, deadline, pending)
        return normalize_rate_limits(result, int(time.time()))
    finally:
        if process is not None:
            try:
                process.stdin.close()
            except OSError:
                pass
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            process.stdout.close()


def query_quota(binary: Optional[str], environ=None):
    if not binary:
        return {"status": "error", "message": "Codex CLI não encontrado; configure o caminho em config.json", "buckets": []}
    try:
        return read_quota([binary, "app-server"], env=child_environment(binary, environ=environ))
    except TimeoutError:
        message = "Tempo esgotado ao consultar o Codex"
    except (OSError, ValueError, RuntimeError) as error:
        message = "Entre na sua assinatura pelo Codex CLI" if "auth" in str(error).lower() else "Não foi possível ler a cota do Codex"
    return {"status": "error", "message": message, "buckets": []}
