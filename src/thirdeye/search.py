from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

from thirdeye.paths import session_dir as _session_dir
from thirdeye.store import Store
from thirdeye.tags import TagStore


@dataclass(frozen=True)
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
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return prefix + text[start:end] + suffix


def search(
    store: Store,
    query: str,
    *,
    platform: str | None = None,
    cwd: str | None = None,
    tags: set[str] | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> Iterator[Hit]:
    needle = query.lower()
    require_tags = bool(tags)
    for meta in store.list_sessions(
        platform=platform,
        cwd=cwd,
        since=since,
        until=until,
    ):
        if require_tags:
            sd = _session_dir(store.config.root, meta.platform, meta.session_id)
            tagged = TagStore(sd).all_tags()
        else:
            tagged = None
        reader = store.reader(meta.session_id)
        for event in reader.iter_events():
            if require_tags:
                assert tagged is not None
                event_tags = tagged.get(event["seq"], set())
                if not tags.issubset(event_tags):
                    continue
            line = _stringify(event)
            if needle in line.lower():
                yield Hit(
                    session_id=meta.session_id,
                    platform=meta.platform,
                    seq=event["seq"],
                    t=event.get("t", ""),
                    snippet=_snippet(line, query),
                )
