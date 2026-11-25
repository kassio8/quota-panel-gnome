#!/usr/bin/env python3
"""Read ChatGPT subscription quota from the local Codex app server."""

import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import time


MAX_RESPONSE_BYTES = 1024 * 1024


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def normalize_rate_limits(result, checked_at):
    """Keep every reported quota window, without inventing missing values."""
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
            used = window.get("usedPercent")
            duration = window.get("windowDurationMins")
            resets = window.get("resetsAt")
            windows.append({
                "durationMinutes": duration
                if isinstance(duration, int) and not isinstance(duration, bool) and duration > 0
                else None,
                "usedPercent": used if _number(used) and 0 <= used <= 100 else None,
                "resetsAt": resets
                if isinstance(resets, int) and not isinstance(resets, bool) and resets > 0
                else None,
            })
        if not windows:
            continue
        windows.sort(key=lambda entry: entry["durationMinutes"] or float("inf"))
        name = snapshot.get("limitName")
        if not isinstance(name, str) or not name.strip():
            name = "Codex" if bucket_id == "codex" else str(bucket_id)
        buckets.append({"id": str(bucket_id), "name": name, "windows": windows})

    buckets.sort(key=lambda entry: (entry["id"] != "codex", entry["name"].lower()))
    has_usage = any(
        window["usedPercent"] is not None
        for bucket in buckets for window in bucket["windows"]
    )
    quota = {
        "status": "ok" if has_usage else "unavailable",
        "checkedAt": checked_at,
        "ordinaryUsageAllowed": result.get("ordinaryUsageAllowed")
        if isinstance(result.get("ordinaryUsageAllowed"), bool) else None,
        "buckets": buckets,
    }
    if not has_usage:
        quota["message"] = "O Codex não informou percentuais de cota"
    return quota


def _send(process, message):
    process.stdin.write(json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n")
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
                    description = error.get("message", "RPC error") if isinstance(error, dict) else "RPC error"
                    raise RuntimeError(description)
                if "result" not in message:
                    raise ValueError("Codex response has no result")
                return message["result"], pending

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Codex did not answer in time")
            if not selector.select(remaining):
                raise TimeoutError("Codex did not answer in time")
            chunk = os.read(process.stdout.fileno(), 65536)
            if not chunk:
                raise RuntimeError("Codex app server closed the connection")
            pending += chunk
            if len(pending) > MAX_RESPONSE_BYTES:
                raise ValueError("Codex response is too large")


def read_quota(command, timeout_seconds=15):
    """Perform one read-only RPC transaction and always reap the child."""
    def on_termination(_signum, _frame):
        raise InterruptedError("Quota reader interrupted")

    previous_handler = signal.signal(signal.SIGTERM, on_termination)
    process = None
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + timeout_seconds
        _send(process, {
            "id": 1,
            "method": "initialize",
            "params": {"clientInfo": {
                "name": "codex_gnome_quota",
                "title": "Codex GNOME Quota",
                "version": "0.1.0",
            }},
        })
        _, pending = _response(process, 1, deadline, b"")
        _send(process, {"method": "initialized", "params": {}})
        _send(process, {"id": 2, "method": "account/rateLimits/read"})
        result, _ = _response(process, 2, deadline, pending)
        return normalize_rate_limits(result, checked_at=int(time.time()))
    finally:
        signal.signal(signal.SIGTERM, previous_handler)
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


def _codex_path():
    saved = Path(__file__).with_name("codex-path.txt")
    if saved.exists():
        candidate = saved.read_text(encoding="utf-8").strip()
        if candidate and os.path.isabs(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return shutil.which("codex")


def main():
    binary = _codex_path()
    if not binary:
        print(json.dumps({"status": "error", "message": "Codex CLI não encontrado"}, ensure_ascii=False))
        return 1
    try:
        quota = read_quota([binary, "app-server"])
    except (OSError, ValueError, RuntimeError, TimeoutError) as error:
        detail = str(error).lower()
        if "authentication" in detail or "auth" in detail:
            message = "Entre na sua assinatura pelo Codex CLI"
        elif isinstance(error, TimeoutError):
            message = "Tempo esgotado ao consultar o Codex"
        else:
            message = "Não foi possível ler a cota do Codex"
        print(json.dumps({"status": "error", "message": message}, ensure_ascii=False))
        return 1
    print(json.dumps(quota, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
