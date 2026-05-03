from __future__ import annotations

import json
import os
import sys

from thirdeye.config import Config
from thirdeye.store import Store

_PLATFORM = "claude"
_ROUTING_KEYS = ("session_id",)


def _read_stdin() -> dict:
    try:
        raw = sys.stdin.read()
    except OSError:
        return {}
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _strip_routing(payload: dict) -> dict:
    return {k: v for k, v in payload.items() if k not in _ROUTING_KEYS}


def _emit(t: str, payload: dict) -> bool:
    sid = payload.get("session_id")
    if not sid:
        return False
    cwd = payload.get("cwd") or os.getcwd()
    Store(Config.load()).append_event(
        session_id=sid,
        platform=_PLATFORM,
        cwd=cwd,
        t=t,
        data=_strip_routing(payload),
    )
    return True


def session_start() -> None:
    _emit("session_start", _read_stdin())


def user_prompt_submit() -> None:
    _emit("user_message", _read_stdin())


def pre_tool_use() -> None:
    _emit("tool_call", _read_stdin())


def post_tool_use() -> None:
    _emit("tool_result", _read_stdin())


def stop() -> None:
    _emit("assistant_message", _read_stdin())


def subagent_stop() -> None:
    _emit("subagent_message", _read_stdin())


def stop_failure() -> None:
    _emit("error", _read_stdin())


def notification() -> None:
    _emit("notification", _read_stdin())


def permission_request() -> None:
    _emit("permission_request", _read_stdin())


def session_end() -> None:
    payload = _read_stdin()
    if _emit("session_end", payload):
        Store(Config.load()).close_session(payload["session_id"], platform=_PLATFORM)
