from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from atrace.config import Config
from atrace.meta import SessionMeta, read_meta, write_meta
from atrace.paths import (
    events_path,
    meta_path,
    platform_dir,
    sessions_root,
)
from atrace.paths import (
    session_dir as _session_dir,
)
from atrace.reader import SessionReader
from atrace.writer import SessionWriter, utc_iso_ms


class Store:
    def __init__(self, config: Config) -> None:
        self.config = config

    def open_session(
        self,
        session_id: str,
        *,
        platform: str,
        cwd: str,
        extra: dict[str, Any] | None = None,
    ) -> SessionWriter:
        sd = _session_dir(self.config.root, platform, session_id)
        return SessionWriter.open(
            sd, session_id=session_id, platform=platform, cwd=cwd, extra=extra
        )

    def list_sessions(
        self,
        *,
        platform: str | None = None,
        cwd: str | None = None,
        status: str | None = None,
    ) -> Iterator[SessionMeta]:
        root = sessions_root(self.config.root)
        if not root.exists():
            return
        platforms = [platform] if platform else sorted(p.name for p in root.iterdir() if p.is_dir())
        for pname in platforms:
            pdir = platform_dir(self.config.root, pname)
            if not pdir.exists():
                continue
            for sd in sorted(pdir.iterdir()):
                if not sd.is_dir():
                    continue
                m = read_meta(meta_path(sd))
                if m is None:
                    continue
                if cwd is not None and m.cwd != cwd:
                    continue
                if status is not None and m.status != status:
                    continue
                yield m

    def resolve_session_id(self, prefix: str) -> tuple[str, str]:
        root = sessions_root(self.config.root)
        candidates: list[tuple[str, str]] = []
        if root.exists():
            for pdir in root.iterdir():
                if not pdir.is_dir():
                    continue
                for sd in pdir.iterdir():
                    if sd.is_dir() and sd.name.startswith(prefix):
                        candidates.append((pdir.name, sd.name))
        if not candidates:
            raise ValueError(f"no session matching prefix {prefix!r}")
        if len(candidates) > 1:
            raise ValueError(f"prefix {prefix!r} ambiguous: {[c[1] for c in candidates]}")
        return candidates[0]

    def reader(self, prefix: str) -> SessionReader:
        platform, sid = self.resolve_session_id(prefix)
        return SessionReader(_session_dir(self.config.root, platform, sid))

    def get_meta(self, prefix: str) -> SessionMeta:
        platform, sid = self.resolve_session_id(prefix)
        m = read_meta(meta_path(_session_dir(self.config.root, platform, sid)))
        if m is None:
            raise ValueError(f"no meta for session {sid}")
        return m

    def stats(self, *, session_id: str | None = None) -> dict[str, Any]:
        if session_id is not None:
            platform, sid = self.resolve_session_id(session_id)
            sd = _session_dir(self.config.root, platform, sid)
            m = read_meta(meta_path(sd))
            log = events_path(sd)
            return {
                "session_id": sid,
                "platform": platform,
                "event_count": m.event_count if m else 0,
                "bytes_compressed": log.stat().st_size if log.exists() else 0,
            }

        total_events = 0
        total_bytes = 0
        sessions = 0
        for m in self.list_sessions():
            sessions += 1
            total_events += m.event_count
            sd = _session_dir(self.config.root, m.platform, m.session_id)
            log = events_path(sd)
            if log.exists():
                total_bytes += log.stat().st_size
        return {
            "session_count": sessions,
            "event_count": total_events,
            "bytes_compressed": total_bytes,
        }

    def append_event(
        self,
        *,
        session_id: str,
        platform: str,
        cwd: str,
        t: str,
        data: Any = None,
    ) -> int:
        sd = _session_dir(self.config.root, platform, session_id)
        w = SessionWriter.open(sd, session_id=session_id, platform=platform, cwd=cwd)
        try:
            seq = w.append(t, data)
        finally:
            write_meta(meta_path(sd), w._meta)
            w.flush_and_detach()
        return seq

    def close_session(self, session_id: str, *, platform: str) -> None:
        sd = _session_dir(self.config.root, platform, session_id)
        if not sd.exists():
            return
        m = read_meta(meta_path(sd))
        if m is None:
            return
        m.status = "closed"
        m.ended_at = utc_iso_ms()
        write_meta(meta_path(sd), m)
