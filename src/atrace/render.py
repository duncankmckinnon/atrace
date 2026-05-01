from __future__ import annotations

import json
from typing import Any


def _is_flat_object(d: dict) -> bool:
    return all(not isinstance(v, (dict, list)) for v in d.values())


def _render_data_terse(data: Any) -> str:
    if data is None:
        return ""
    if isinstance(data, (str, int, float, bool)):
        return str(data)
    if isinstance(data, dict):
        if _is_flat_object(data):
            return " ".join(str(v) for v in data.values())
        return json.dumps(data, default=str, separators=(",", ":"), ensure_ascii=False)
    if isinstance(data, list):
        return json.dumps(data, default=str, separators=(",", ":"), ensure_ascii=False)
    return repr(data)


def render_event_terse(event: dict, *, width: int = 120) -> str:
    parts = [str(event["seq"]), event["t"]]
    body = _render_data_terse(event.get("data"))
    if body:
        parts.append(body)
    line = " ".join(parts)
    if width and len(line) > width:
        line = line[: width - 1] + "\u2026"
    return line


def render_event_jsonl(event: dict) -> str:
    return json.dumps(event, default=str, separators=(",", ":"), ensure_ascii=False)


def _render_value_tree(value: Any, indent: int) -> str:
    pad = "  " * indent
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{pad}{k}:")
                lines.append(_render_value_tree(v, indent + 1))
            else:
                lines.append(f"{pad}{k}: {v}")
        return "\n".join(lines)
    if isinstance(value, list):
        return "\n".join(f"{pad}- {item}" for item in value)
    return f"{pad}{value}"


def render_event_tree(event: dict) -> str:
    head = f"#{event['seq']} {event['t']}  ({event['ts']})"
    data = event.get("data")
    if data is None:
        return head
    return head + "\n" + _render_value_tree(data, indent=1)
