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
