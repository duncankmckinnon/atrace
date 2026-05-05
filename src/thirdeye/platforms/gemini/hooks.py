from __future__ import annotations

import json
import os
import sys

from thirdeye.config import Config
from thirdeye.store import Store

_PLATFORM = "gemini"

# Routing keys we strip from event data because they're already used as
# routing fields when calling Store.append_event, OR because they're
# variants we don't want duplicated in storage.
_STRIP_KEYS = frozenset(
    {
        "session_id",
        "sessionId",
        "cwd",
        "workingDir",
        "working_dir",
    }
)


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


def _flex_get(d: dict, *keys, default=None):
    """Try multiple key names, return first non-None/non-empty value."""
    for key in keys:
        v = d.get(key)
        if v is not None and v != "":
            return v
    return default


def _strip_payload(payload: dict) -> dict:
    return {k: v for k, v in payload.items() if k not in _STRIP_KEYS}


def _print_response() -> None:
    """Gemini hooks must print {} to stdout when they finish."""
    print(json.dumps({}))


def _emit(t: str, payload: dict) -> bool:
    sid = _flex_get(payload, "session_id", "sessionId")
    if not sid:
        return False
    cwd = _flex_get(payload, "cwd", "workingDir", "working_dir") or os.getcwd()
    Store(Config.load()).append_event(
        session_id=sid,
        platform=_PLATFORM,
        cwd=cwd,
        t=t,
        data=_strip_payload(payload),
    )
    return True


def session_start() -> None:
    try:
        _emit("session_start", _read_stdin())
    except Exception:
        pass
    finally:
        _print_response()


def session_end() -> None:
    try:
        payload = _read_stdin()
        if _emit("session_end", payload):
            sid = _flex_get(payload, "session_id", "sessionId")
            Store(Config.load()).close_session(sid, platform=_PLATFORM)
    except Exception:
        pass
    finally:
        _print_response()


def before_agent() -> None:
    try:
        _emit("user_message", _read_stdin())
    except Exception:
        pass
    finally:
        _print_response()


def after_agent() -> None:
    try:
        _emit("assistant_message", _read_stdin())
    except Exception:
        pass
    finally:
        _print_response()


def before_model() -> None:
    try:
        _emit("model_request", _read_stdin())
    except Exception:
        pass
    finally:
        _print_response()


def after_model() -> None:
    try:
        _emit("model_response", _read_stdin())
    except Exception:
        pass
    finally:
        _print_response()


def before_tool() -> None:
    try:
        _emit("tool_call", _read_stdin())
    except Exception:
        pass
    finally:
        _print_response()


def after_tool() -> None:
    try:
        _emit("tool_result", _read_stdin())
    except Exception:
        pass
    finally:
        _print_response()
