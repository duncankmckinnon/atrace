from __future__ import annotations

import fcntl
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from atrace.codec import encode_event
from atrace.index import IndexReader, IndexWriter, rebuild_index
from atrace.meta import SessionMeta, read_meta, write_meta
from atrace.paths import events_path, index_path, meta_path


def _utc_iso_ms() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def utc_iso_ms() -> str:
    return _utc_iso_ms()


class SessionWriter:
    def __init__(self, session_dir: Path, meta: SessionMeta) -> None:
        self.session_dir = session_dir
        self._events = events_path(session_dir)
        self._idx = index_path(session_dir)
        self._meta_path = meta_path(session_dir)
        self._meta = meta
        self._index_w = IndexWriter(self._idx)
        if self._events.exists():
            log_size = self._events.stat().st_size
            if log_size > 0 and self._idx.stat().st_size == 0:
                self._index_w.close()
                rebuild_index(self._events, self._idx)
                self._index_w = IndexWriter(self._idx)
        self._next_seq = IndexReader(self._idx).count()

    @classmethod
    def open(
        cls,
        session_dir: Path,
        *,
        session_id: str,
        platform: str,
        cwd: str,
        extra: dict[str, Any] | None = None,
    ) -> "SessionWriter":
        session_dir.mkdir(parents=True, exist_ok=True)
        existing = read_meta(meta_path(session_dir))
        if existing is None:
            meta = SessionMeta(
                session_id=session_id,
                platform=platform,
                cwd=cwd,
                started_at=_utc_iso_ms(),
                ended_at=None,
                status="open",
                event_count=0,
                last_seq=-1,
                last_ts=None,
                extra=extra or {},
            )
        else:
            existing.status = "open"
            existing.ended_at = None
            meta = existing
        write_meta(meta_path(session_dir), meta)
        return cls(session_dir, meta)

    def append(self, t: str, data: Any = None) -> int:
        seq = self._next_seq
        ts = _utc_iso_ms()
        event: dict[str, Any] = {"t": t, "ts": ts, "seq": seq}
        if data is not None:
            event["data"] = data
        frame = encode_event(event)

        with open(self._events, "ab") as fp:
            fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
            try:
                offset = fp.tell()
                fp.write(frame)
                fp.flush()
                os.fsync(fp.fileno())
            finally:
                fcntl.flock(fp.fileno(), fcntl.LOCK_UN)
        self._index_w.append(offset)

        self._next_seq += 1
        self._meta.event_count = self._next_seq
        self._meta.last_seq = seq
        self._meta.last_ts = ts
        return seq

    def flush_and_detach(self) -> None:
        self._index_w.close()

    def close(self, *, status: str = "closed") -> None:
        self._index_w.close()
        self._meta.status = status
        self._meta.ended_at = _utc_iso_ms()
        self._meta.event_count = self._next_seq
        self._meta.last_seq = self._next_seq - 1 if self._next_seq > 0 else -1
        write_meta(self._meta_path, self._meta)

    def __enter__(self) -> "SessionWriter":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
