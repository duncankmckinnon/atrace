from __future__ import annotations

import json
import os
import sys

from thirdeye.config import Config
from thirdeye.store import Store

_PLATFORM = "codex"

# Strip routing keys from stored event data because they're routing fields
# OR camel/kebab variants we don't need duplicated in storage.
_STRIP_KEYS = frozenset({
    "thread-id", "thread_id", "threadId",
    "cwd", "working-directory", "working_directory",
})


def _read_argv() -> dict:
    if len(sys.argv) < 2:
        return {}
    raw = sys.argv[1]
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _flex_get(d: dict, *keys, default=None):
    for key in keys:
        v = d.get(key)
        if v is not None and v != "":
            return v
    return default


def _strip_payload(payload: dict) -> dict:
    return {k: v for k, v in payload.items() if k not in _STRIP_KEYS}


def _emit(t: str, payload: dict) -> bool:
    sid = _flex_get(payload, "thread-id", "thread_id", "threadId")
    if not sid:
        return False
    cwd = _flex_get(payload, "cwd", "working-directory", "working_directory") or os.getcwd()
    Store(Config.load()).append_event(
        session_id=sid,
        platform=_PLATFORM,
        cwd=cwd,
        t=t,
        data=_strip_payload(payload),
    )
    return True


def notify() -> None:
    try:
        payload = _read_argv()
        if payload.get("type") != "agent-turn-complete":
            return
        _emit("agent_turn", payload)
    except Exception:
        pass
