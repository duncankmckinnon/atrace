from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from atrace.codec import encode_event
from atrace.index import IndexWriter
from atrace.meta import SessionMeta, write_meta
from atrace.paths import events_path, index_path, meta_path


def _now_iso() -> str:
    dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


class SessionWriter:
    def __init__(
        self, session_dir: Path, session_id: str, platform: str, cwd: str
    ) -> None:
        self.session_dir = session_dir
        self._session_id = session_id
        self._platform = platform
        self._cwd = cwd
        self._seq = 0
        self._started_at = _now_iso()
        self._last_ts: str | None = None

        session_dir.mkdir(parents=True, exist_ok=True)
        self._log_fp = open(events_path(session_dir), "ab")
        self._idx = IndexWriter(index_path(session_dir))
        self._write_meta("open")

    @classmethod
    def open(
        cls, session_dir: Path, *, session_id: str, platform: str, cwd: str
    ) -> SessionWriter:
        return cls(session_dir, session_id, platform, cwd)

    def append(self, t: str, data: Any = None) -> int:
        ts = _now_iso()
        event: dict[str, Any] = {"t": t, "ts": ts, "seq": self._seq}
        if data is not None:
            event["data"] = data
        frame = encode_event(event)
        offset = self._log_fp.tell()
        self._log_fp.write(frame)
        self._log_fp.flush()
        os.fsync(self._log_fp.fileno())
        self._idx.append(offset)
        self._last_ts = ts
        seq = self._seq
        self._seq += 1
        self._write_meta("open")
        return seq

    def close(self) -> None:
        self._write_meta("closed")
        self._log_fp.close()
        self._idx.close()

    def _write_meta(self, status: str) -> None:
        meta = SessionMeta(
            session_id=self._session_id,
            platform=self._platform,
            cwd=self._cwd,
            started_at=self._started_at,
            ended_at=_now_iso() if status == "closed" else None,
            status=status,
            event_count=self._seq,
            last_seq=self._seq - 1,
            last_ts=self._last_ts,
        )
        write_meta(meta_path(self.session_dir), meta)
