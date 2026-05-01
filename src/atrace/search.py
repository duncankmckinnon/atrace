from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterator

from atrace.store import Store


@dataclass
class Hit:
    session_id: str
    platform: str
    seq: int
    t: str
    snippet: str


def _stringify(event: dict) -> str:
    return json.dumps(event, default=str, ensure_ascii=False)


def _snippet(text: str, query: str, window: int = 80) -> str:
    idx = text.lower().find(query.lower())
    if idx == -1:
        return text[:window]
    half = window // 2
    start = max(0, idx - half)
    end = min(len(text), idx + len(query) + half)
    prefix = "\u2026" if start > 0 else ""
    suffix = "\u2026" if end < len(text) else ""
    return prefix + text[start:end] + suffix


def search(
    store: Store,
    query: str,
    *,
    platform: str | None = None,
    cwd: str | None = None,
) -> Iterator[Hit]:
    needle = query.lower()
    for meta in store.list_sessions(platform=platform, cwd=cwd):
        reader = store.reader(meta.session_id)
        for event in reader.iter_events():
            line = _stringify(event)
            if needle in line.lower():
                yield Hit(
                    session_id=meta.session_id,
                    platform=meta.platform,
                    seq=event["seq"],
                    t=event.get("t", ""),
                    snippet=_snippet(line, query),
                )
