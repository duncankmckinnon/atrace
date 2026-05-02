from __future__ import annotations

from pathlib import Path

import pytest

from atrace.config import Config
from atrace.meta import SessionMeta, write_meta
from atrace.paths import meta_path, events_path, session_dir, sessions_root
from atrace.reader import SessionReader
from atrace.store import Store
from atrace.writer import SessionWriter


# -- open_session --------------------------------------------------------------


class TestOpenSession:
    def test_returns_writer(self, tmp_store: Store):
        with tmp_store.open_session("01J9G7", platform="claude", cwd="/p") as w:
            assert isinstance(w, SessionWriter)

    def test_writer_append_returns_seq_zero(self, tmp_store: Store):
        with tmp_store.open_session("01J9G7", platform="claude", cwd="/p") as w:
            assert w.append("user_message", "hi") == 0

    def test_creates_session_dir(self, tmp_store: Store):
        with tmp_store.open_session("01J9G7", platform="claude", cwd="/p") as w:
            sd = session_dir(tmp_store.config.root, "claude", "01J9G7")
            assert sd.is_dir()

    def test_passes_extra_to_writer(self, tmp_store: Store):
        extra = {"model": "opus"}
        with tmp_store.open_session(
            "01J9G7", platform="claude", cwd="/p", extra=extra
        ) as w:
            w.append("x", 1)
        m = tmp_store.get_meta("01J9G7")
        assert m.extra == extra

    def test_extra_defaults_none(self, tmp_store: Store):
        with tmp_store.open_session("01J9G7", platform="claude", cwd="/p") as w:
            w.append("x", 1)
        m = tmp_store.get_meta("01J9G7")
        assert m.extra == {}


# -- list_sessions -------------------------------------------------------------


class TestListSessions:
    def test_all(self, populated_store: Store):
        metas = list(populated_store.list_sessions())
        assert sorted(m.session_id for m in metas) == ["01J9G7XK4P", "02ABCDEF12"]

    def test_returns_session_meta_objects(self, populated_store: Store):
        metas = list(populated_store.list_sessions())
        for m in metas:
            assert isinstance(m, SessionMeta)

    def test_filter_platform(self, populated_store: Store):
        metas = list(populated_store.list_sessions(platform="claude"))
        assert [m.session_id for m in metas] == ["01J9G7XK4P"]

    def test_filter_platform_cursor(self, populated_store: Store):
        metas = list(populated_store.list_sessions(platform="cursor"))
        assert [m.session_id for m in metas] == ["02ABCDEF12"]

    def test_filter_cwd(self, populated_store: Store):
        metas = list(populated_store.list_sessions(cwd="/proj/b"))
        assert [m.session_id for m in metas] == ["02ABCDEF12"]

    def test_filter_status(self, tmp_store: Store):
        with tmp_store.open_session("AAAA", platform="claude", cwd="/p") as w:
            w.append("x", 1)
        with tmp_store.open_session("BBBB", platform="claude", cwd="/p") as w:
            w.append("x", 1)
        # Reopen BBBB so it stays open
        w2 = tmp_store.open_session("BBBB", platform="claude", cwd="/p")
        metas = list(tmp_store.list_sessions(status="open"))
        assert [m.session_id for m in metas] == ["BBBB"]
        w2.close()

    def test_filter_platform_no_matches(self, populated_store: Store):
        metas = list(populated_store.list_sessions(platform="codex"))
        assert metas == []

    def test_filter_cwd_no_matches(self, populated_store: Store):
        metas = list(populated_store.list_sessions(cwd="/nonexistent"))
        assert metas == []

    def test_empty_store(self, tmp_store: Store):
        metas = list(tmp_store.list_sessions())
        assert metas == []

    def test_sessions_root_doesnt_exist(self, tmp_path: Path):
        store = Store(Config(root=tmp_path / "nonexistent"))
        metas = list(store.list_sessions())
        assert metas == []

    def test_ignores_non_directory_entries(self, tmp_store: Store):
        with tmp_store.open_session("01J9G7", platform="claude", cwd="/p") as w:
            w.append("x", 1)
        # Create a stray file inside platform dir
        stray = sessions_root(tmp_store.config.root) / "claude" / "not-a-dir.txt"
        stray.write_text("junk")
        metas = list(tmp_store.list_sessions())
        assert len(metas) == 1

    def test_ignores_session_dir_without_meta(self, tmp_store: Store):
        # Create a session dir with no meta.yaml
        sd = session_dir(tmp_store.config.root, "claude", "ORPHAN")
        sd.mkdir(parents=True)
        metas = list(tmp_store.list_sessions())
        assert metas == []

    def test_multiple_platforms(self, tmp_store: Store):
        for p in ["claude", "cursor", "codex"]:
            with tmp_store.open_session(f"SID_{p}", platform=p, cwd="/p") as w:
                w.append("x", 1)
        metas = list(tmp_store.list_sessions())
        assert len(metas) == 3
        assert sorted(m.platform for m in metas) == ["claude", "codex", "cursor"]


# -- resolve_session_id --------------------------------------------------------


class TestResolveSessionId:
    def test_unique_prefix(self, populated_store: Store):
        assert populated_store.resolve_session_id("01J9") == ("claude", "01J9G7XK4P")

    def test_full_id(self, populated_store: Store):
        assert populated_store.resolve_session_id("02ABCDEF12") == (
            "cursor",
            "02ABCDEF12",
        )

    def test_no_match_raises(self, populated_store: Store):
        with pytest.raises(ValueError, match="no session matching"):
            populated_store.resolve_session_id("ZZZZZ")

    def test_ambiguous_prefix_raises(self, tmp_store: Store):
        with tmp_store.open_session("AB1111", platform="claude", cwd="/p") as w:
            w.append("x", 1)
        with tmp_store.open_session("AB2222", platform="cursor", cwd="/p") as w:
            w.append("x", 1)
        with pytest.raises(ValueError, match="ambiguous"):
            tmp_store.resolve_session_id("AB")

    def test_empty_store_raises(self, tmp_store: Store):
        with pytest.raises(ValueError, match="no session matching"):
            tmp_store.resolve_session_id("anything")

    def test_single_char_prefix(self, populated_store: Store):
        # "0" matches both sessions -> ambiguous
        with pytest.raises(ValueError, match="ambiguous"):
            populated_store.resolve_session_id("0")

    def test_returns_platform_and_sid_tuple(self, populated_store: Store):
        result = populated_store.resolve_session_id("01J9G7XK4P")
        assert isinstance(result, tuple)
        assert len(result) == 2
        platform, sid = result
        assert platform == "claude"
        assert sid == "01J9G7XK4P"


# -- reader --------------------------------------------------------------------


class TestReader:
    def test_returns_session_reader(self, populated_store: Store):
        r = populated_store.reader("01J9")
        assert isinstance(r, SessionReader)

    def test_reader_can_iterate_events(self, populated_store: Store):
        r = populated_store.reader("01J9")
        events = list(r.iter_events())
        assert len(events) == 2
        assert events[0]["t"] == "user_message"
        assert events[1]["t"] == "assistant_message"

    def test_reader_no_match_raises(self, populated_store: Store):
        with pytest.raises(ValueError, match="no session matching"):
            populated_store.reader("ZZZZZ")


# -- get_meta ------------------------------------------------------------------


class TestGetMeta:
    def test_returns_meta(self, populated_store: Store):
        m = populated_store.get_meta("01J9G7XK4P")
        assert isinstance(m, SessionMeta)
        assert m.session_id == "01J9G7XK4P"
        assert m.platform == "claude"

    def test_by_prefix(self, populated_store: Store):
        m = populated_store.get_meta("02AB")
        assert m.session_id == "02ABCDEF12"
        assert m.platform == "cursor"

    def test_no_match_raises(self, populated_store: Store):
        with pytest.raises(ValueError, match="no session matching"):
            populated_store.get_meta("ZZZZZ")

    def test_event_count(self, populated_store: Store):
        m = populated_store.get_meta("01J9")
        assert m.event_count == 2

    def test_cwd(self, populated_store: Store):
        m = populated_store.get_meta("01J9")
        assert m.cwd == "/proj/a"


# -- stats ---------------------------------------------------------------------


class TestStats:
    def test_session_stats(self, populated_store: Store):
        s = populated_store.stats(session_id="01J9G7XK4P")
        assert s["event_count"] == 2
        assert s["bytes_compressed"] > 0
        assert s["session_id"] == "01J9G7XK4P"
        assert s["platform"] == "claude"

    def test_session_stats_by_prefix(self, populated_store: Store):
        s = populated_store.stats(session_id="02AB")
        assert s["event_count"] == 1
        assert s["platform"] == "cursor"

    def test_global_stats(self, populated_store: Store):
        s = populated_store.stats()
        assert s["session_count"] == 2
        assert s["event_count"] == 3
        assert s["bytes_compressed"] > 0

    def test_global_stats_empty_store(self, tmp_store: Store):
        s = tmp_store.stats()
        assert s["session_count"] == 0
        assert s["event_count"] == 0
        assert s["bytes_compressed"] == 0

    def test_session_stats_no_match_raises(self, populated_store: Store):
        with pytest.raises(ValueError, match="no session matching"):
            populated_store.stats(session_id="ZZZZZ")

    def test_session_stats_bytes_increases_with_events(self, tmp_store: Store):
        with tmp_store.open_session("SID1", platform="claude", cwd="/p") as w:
            w.append("x", "short")
        s1 = tmp_store.stats(session_id="SID1")
        with tmp_store.open_session("SID2", platform="claude", cwd="/p") as w:
            for i in range(20):
                w.append("x", f"data_{i}" * 50)
        s2 = tmp_store.stats(session_id="SID2")
        assert s2["bytes_compressed"] > s1["bytes_compressed"]


# -- constructor ---------------------------------------------------------------


class TestStoreInit:
    def test_config_stored(self, tmp_path: Path):
        cfg = Config(root=tmp_path)
        store = Store(cfg)
        assert store.config is cfg


# -- append_event --------------------------------------------------------------


class TestAppendEvent:
    def test_one_shot(self, tmp_store: Store):
        seq = tmp_store.append_event(
            session_id="01J9G7XK4P", platform="claude", cwd="/p",
            t="user_message", data="hi",
        )
        assert seq == 0
        metas = list(tmp_store.list_sessions())
        assert len(metas) == 1
        assert metas[0].session_id == "01J9G7XK4P"
        assert metas[0].status == "open"
        assert metas[0].event_count == 1

    def test_appends_to_existing_session(self, tmp_store: Store):
        tmp_store.append_event(
            session_id="01J9G7XK4P", platform="claude", cwd="/p",
            t="user_message", data="hi",
        )
        seq = tmp_store.append_event(
            session_id="01J9G7XK4P", platform="claude", cwd="/p",
            t="assistant_message", data="hello",
        )
        assert seq == 1

    def test_returns_int(self, tmp_store: Store):
        result = tmp_store.append_event(
            session_id="SID1", platform="claude", cwd="/p",
            t="x", data=1,
        )
        assert isinstance(result, int)

    def test_data_none_accepted(self, tmp_store: Store):
        seq = tmp_store.append_event(
            session_id="SID1", platform="claude", cwd="/p",
            t="session_start",
        )
        assert seq == 0

    def test_complex_data(self, tmp_store: Store):
        payload = {"tool_name": "Read", "args": {"path": "/foo"}, "nested": [1, 2]}
        seq = tmp_store.append_event(
            session_id="SID1", platform="claude", cwd="/p",
            t="tool_call", data=payload,
        )
        assert seq == 0
        r = tmp_store.reader("SID1")
        events = list(r.iter_events())
        assert events[0]["data"] == payload

    def test_event_readable_after_append(self, tmp_store: Store):
        tmp_store.append_event(
            session_id="SID1", platform="claude", cwd="/p",
            t="user_message", data="hello",
        )
        r = tmp_store.reader("SID1")
        events = list(r.iter_events())
        assert len(events) == 1
        assert events[0]["t"] == "user_message"
        assert events[0]["data"] == "hello"

    def test_many_sequential_appends(self, tmp_store: Store):
        for i in range(10):
            seq = tmp_store.append_event(
                session_id="SID1", platform="claude", cwd="/p",
                t=f"evt_{i}", data=i,
            )
            assert seq == i
        m = tmp_store.get_meta("SID1")
        assert m.event_count == 10

    def test_different_sessions_independent(self, tmp_store: Store):
        tmp_store.append_event(
            session_id="SID_A", platform="claude", cwd="/p",
            t="a", data=1,
        )
        tmp_store.append_event(
            session_id="SID_B", platform="claude", cwd="/q",
            t="b", data=2,
        )
        metas = sorted(tmp_store.list_sessions(), key=lambda m: m.session_id)
        assert len(metas) == 2
        assert metas[0].session_id == "SID_A"
        assert metas[1].session_id == "SID_B"

    def test_session_stays_open_after_append(self, tmp_store: Store):
        tmp_store.append_event(
            session_id="SID1", platform="claude", cwd="/p",
            t="x", data=1,
        )
        m = tmp_store.get_meta("SID1")
        assert m.status == "open"
        assert m.ended_at is None

    def test_different_platforms(self, tmp_store: Store):
        tmp_store.append_event(
            session_id="SID1", platform="claude", cwd="/p",
            t="x", data=1,
        )
        tmp_store.append_event(
            session_id="SID2", platform="cursor", cwd="/p",
            t="y", data=2,
        )
        claude_sessions = list(tmp_store.list_sessions(platform="claude"))
        cursor_sessions = list(tmp_store.list_sessions(platform="cursor"))
        assert len(claude_sessions) == 1
        assert len(cursor_sessions) == 1


# -- close_session -------------------------------------------------------------


class TestCloseSession:
    def test_marks_closed(self, tmp_store: Store):
        tmp_store.append_event(
            session_id="01J9G7XK4P", platform="claude", cwd="/p",
            t="x", data=1,
        )
        tmp_store.close_session("01J9G7XK4P", platform="claude")
        m = next(tmp_store.list_sessions())
        assert m.status == "closed"
        assert m.ended_at is not None

    def test_no_op_for_missing_session(self, tmp_store: Store):
        tmp_store.close_session("does-not-exist", platform="claude")

    def test_no_op_for_missing_platform(self, tmp_store: Store):
        tmp_store.append_event(
            session_id="SID1", platform="claude", cwd="/p",
            t="x", data=1,
        )
        tmp_store.close_session("SID1", platform="cursor")
        # Original session should still be open
        m = tmp_store.get_meta("SID1")
        assert m.status == "open"

    def test_sets_ended_at_timestamp(self, tmp_store: Store):
        import re
        ts_re = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
        tmp_store.append_event(
            session_id="SID1", platform="claude", cwd="/p",
            t="x", data=1,
        )
        tmp_store.close_session("SID1", platform="claude")
        m = tmp_store.get_meta("SID1")
        assert ts_re.match(m.ended_at)

    def test_preserves_event_count(self, tmp_store: Store):
        for i in range(3):
            tmp_store.append_event(
                session_id="SID1", platform="claude", cwd="/p",
                t=f"evt_{i}", data=i,
            )
        tmp_store.close_session("SID1", platform="claude")
        m = tmp_store.get_meta("SID1")
        assert m.event_count == 3

    def test_preserves_started_at(self, tmp_store: Store):
        tmp_store.append_event(
            session_id="SID1", platform="claude", cwd="/p",
            t="x", data=1,
        )
        started = tmp_store.get_meta("SID1").started_at
        tmp_store.close_session("SID1", platform="claude")
        m = tmp_store.get_meta("SID1")
        assert m.started_at == started

    def test_close_then_append_reopens(self, tmp_store: Store):
        tmp_store.append_event(
            session_id="SID1", platform="claude", cwd="/p",
            t="a", data=1,
        )
        tmp_store.close_session("SID1", platform="claude")
        assert tmp_store.get_meta("SID1").status == "closed"
        seq = tmp_store.append_event(
            session_id="SID1", platform="claude", cwd="/p",
            t="b", data=2,
        )
        assert seq == 1
        assert tmp_store.get_meta("SID1").status == "open"

    def test_idempotent_close(self, tmp_store: Store):
        tmp_store.append_event(
            session_id="SID1", platform="claude", cwd="/p",
            t="x", data=1,
        )
        tmp_store.close_session("SID1", platform="claude")
        tmp_store.close_session("SID1", platform="claude")
        m = tmp_store.get_meta("SID1")
        assert m.status == "closed"

    def test_no_op_when_session_dir_exists_but_no_meta(self, tmp_store: Store):
        sd = session_dir(tmp_store.config.root, "claude", "ORPHAN")
        sd.mkdir(parents=True)
        tmp_store.close_session("ORPHAN", platform="claude")
