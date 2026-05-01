from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = 1


@dataclass
class SessionMeta:
    session_id: str
    platform: str
    cwd: str
    started_at: str
    ended_at: str | None
    status: str  # "open" | "closed" | "stale"
    event_count: int
    last_seq: int  # -1 if no events yet
    last_ts: str | None
    extra: dict[str, Any] = field(default_factory=dict)


def write_meta(path: Path, meta: SessionMeta) -> None:
    payload = {"schema_version": SCHEMA_VERSION, **asdict(meta)}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        yaml.safe_dump(payload, f, sort_keys=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def read_meta(path: Path) -> SessionMeta | None:
    if not path.exists():
        return None
    with open(path) as f:
        raw = yaml.safe_load(f) or {}
    raw.pop("schema_version", None)
    raw.setdefault("extra", {})
    return SessionMeta(**raw)
