"""Tests for atrace.paths — pure path-layout helpers."""
from pathlib import Path

from atrace.paths import (
    events_path,
    index_path,
    meta_path,
    platform_dir,
    session_dir,
    sessions_root,
)


class TestSessionsRoot:
    def test_appends_traces(self):
        assert sessions_root(Path("/tmp/atrace")) == Path("/tmp/atrace/traces")

    def test_preserves_home_path(self):
        home = Path("/home/user/.atrace")
        assert sessions_root(home) == home / "traces"


class TestPlatformDir:
    def test_claude(self):
        assert platform_dir(Path("/tmp/atrace"), "claude") == Path(
            "/tmp/atrace/traces/claude"
        )

    def test_cursor(self):
        assert platform_dir(Path("/tmp/atrace"), "cursor") == Path(
            "/tmp/atrace/traces/cursor"
        )

    def test_nested_under_sessions_root(self):
        home = Path("/tmp/atrace")
        assert platform_dir(home, "gemini") == sessions_root(home) / "gemini"


class TestSessionDir:
    def test_basic(self):
        assert session_dir(Path("/tmp/atrace"), "claude", "01J9G7") == Path(
            "/tmp/atrace/traces/claude/01J9G7"
        )

    def test_full_ulid(self):
        ulid = "01J9G7XK4PABCDEFGHJKMNPQRS"
        result = session_dir(Path("/tmp/atrace"), "codex", ulid)
        assert result == Path(f"/tmp/atrace/traces/codex/{ulid}")

    def test_nested_under_platform_dir(self):
        home = Path("/tmp/atrace")
        sid = "01J9G7XK4P"
        assert session_dir(home, "claude", sid) == (
            platform_dir(home, "claude") / sid
        )


class TestEventFiles:
    def setup_method(self):
        self.sd = Path("/tmp/atrace/traces/claude/01J9G7")

    def test_events_path(self):
        assert events_path(self.sd) == self.sd / "events.alog"

    def test_index_path(self):
        assert index_path(self.sd) == self.sd / "events.idx"

    def test_meta_path(self):
        assert meta_path(self.sd) == self.sd / "meta.yaml"

    def test_file_extensions_are_distinct(self):
        paths = {events_path(self.sd), index_path(self.sd), meta_path(self.sd)}
        assert len(paths) == 3

    def test_all_under_session_dir(self):
        for fn in (events_path, index_path, meta_path):
            assert fn(self.sd).parent == self.sd
