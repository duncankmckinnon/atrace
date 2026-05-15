from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from thirdeye.paths import sessions_root, usage_db_path, usage_jsonl_path
from thirdeye.usage.errlog import log_capture_error


SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS usage (
    session_id     TEXT NOT NULL,
    seq            INTEGER NOT NULL,
    ts             TEXT NOT NULL,
    platform       TEXT NOT NULL,
    model          TEXT NOT NULL,
    input_tokens   INTEGER NOT NULL,
    output_tokens  INTEGER NOT NULL,
    total_tokens   INTEGER NOT NULL,
    PRIMARY KEY (session_id, seq)
);
CREATE INDEX IF NOT EXISTS idx_usage_model    ON usage (model);
CREATE INDEX IF NOT EXISTS idx_usage_ts       ON usage (ts);
CREATE INDEX IF NOT EXISTS idx_usage_platform ON usage (platform);
CREATE TABLE IF NOT EXISTS usage_sync (
    session_id      TEXT PRIMARY KEY,
    last_jsonl_size INTEGER NOT NULL
);
"""


class UsageIndex:
    def __init__(self, thirdeye_home: Path) -> None:
        self.thirdeye_home = thirdeye_home
        self.db_path = usage_db_path(thirdeye_home)

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.executescript(SCHEMA_SQL)
        current = conn.execute("PRAGMA user_version").fetchone()[0]
        if current < SCHEMA_VERSION:
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            conn.commit()
        return conn

    def refresh(self, conn: sqlite3.Connection) -> int:
        """Pull new rows from every session's usage.jsonl into the DB.

        Returns the total number of rows inserted across all sessions.
        Anomalies (shrunk sidecars, malformed lines) are logged but do not
        raise.
        """
        inserted = 0
        root = sessions_root(self.thirdeye_home)
        if not root.exists():
            return 0
        for platform_dir_ in sorted(root.iterdir()):
            if not platform_dir_.is_dir():
                continue
            for session_dir_ in sorted(platform_dir_.iterdir()):
                if not session_dir_.is_dir():
                    continue
                inserted += self._refresh_one(conn, session_dir_.name, session_dir_)
        conn.commit()
        return inserted

    def refresh_session(
        self, conn: sqlite3.Connection, session_id: str, session_dir_: Path
    ) -> int:
        n = self._refresh_one(conn, session_id, session_dir_)
        conn.commit()
        return n

    def _refresh_one(
        self, conn: sqlite3.Connection, sid: str, session_dir_: Path
    ) -> int:
        jsonl = usage_jsonl_path(session_dir_)
        if not jsonl.exists():
            return 0
        try:
            current_size = jsonl.stat().st_size
        except FileNotFoundError:
            return 0

        cur = conn.execute(
            "SELECT last_jsonl_size FROM usage_sync WHERE session_id = ?", (sid,)
        ).fetchone()
        last_size = cur[0] if cur else 0

        if current_size == last_size:
            return 0
        if current_size < last_size:
            log_capture_error(
                thirdeye_home=self.thirdeye_home,
                phase="index_sync",
                message=f"sidecar shrank from {last_size} to {current_size}",
                session_id=sid,
                source_path=str(jsonl),
            )
            conn.execute("DELETE FROM usage WHERE session_id = ?", (sid,))
            last_size = 0

        inserted = 0
        with jsonl.open("rb") as f:
            f.seek(last_size)
            for raw in f:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    log_capture_error(
                        thirdeye_home=self.thirdeye_home,
                        phase="index_sync",
                        message="malformed jsonl line",
                        session_id=sid,
                        source_path=str(jsonl),
                    )
                    continue
                try:
                    cursor = conn.execute(
                        "INSERT OR IGNORE INTO usage "
                        "(session_id, seq, ts, platform, model, "
                        "input_tokens, output_tokens, total_tokens) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            row["session_id"],
                            int(row["seq"]),
                            row["ts"],
                            row["platform"],
                            row["model"],
                            int(row["input_tokens"]),
                            int(row["output_tokens"]),
                            int(row["total_tokens"]),
                        ),
                    )
                    inserted += cursor.rowcount
                except (KeyError, ValueError, sqlite3.Error) as e:
                    log_capture_error(
                        thirdeye_home=self.thirdeye_home,
                        phase="index_sync",
                        error=e,
                        session_id=sid,
                        source_path=str(jsonl),
                    )

        conn.execute(
            "INSERT INTO usage_sync (session_id, last_jsonl_size) "
            "VALUES (?, ?) "
            "ON CONFLICT (session_id) DO UPDATE SET last_jsonl_size = excluded.last_jsonl_size",
            (sid, current_size),
        )
        return inserted
