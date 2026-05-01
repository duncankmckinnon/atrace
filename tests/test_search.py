from __future__ import annotations

from pathlib import Path

import pytest

from atrace.config import Config
from atrace.search import Hit, search, _snippet, _stringify
from atrace.store import Store


# -- search: basic matching ----------------------------------------------------


class TestSearchBasic:
    def test_finds_string_in_data(self, populated_store: Store):
        hits = list(search(populated_store, "hello"))
        assert len(hits) == 1
        assert hits[0].session_id == "01J9G7XK4P"
        assert "hello" in hits[0].snippet

    def test_finds_string_across_sessions(self, populated_store: Store):
        hits = list(search(populated_store, "hi from"))
        assert len(hits) == 2
        session_ids = {h.session_id for h in hits}
        assert session_ids == {"01J9G7XK4P", "02ABCDEF12"}

    def test_no_matches(self, populated_store: Store):
        assert list(search(populated_store, "nonexistent_string_xyz")) == []

    def test_case_insensitive(self, populated_store: Store):
        hits_lower = list(search(populated_store, "hello"))
        hits_upper = list(search(populated_store, "HELLO"))
        assert len(hits_lower) == len(hits_upper) == 1
        assert hits_lower[0].session_id == hits_upper[0].session_id

    def test_matches_event_type_field(self, populated_store: Store):
        hits = list(search(populated_store, "user_message"))
        assert len(hits) == 2

    def test_matches_seq_number(self, populated_store: Store):
        # "seq": 0 appears in all events; search for it via JSON repr
        hits = list(search(populated_store, '"seq": 0'))
        assert len(hits) >= 2


# -- search: Hit fields -------------------------------------------------------


class TestSearchHitFields:
    def test_hit_has_session_id(self, populated_store: Store):
        hits = list(search(populated_store, "hi from claude"))
        assert len(hits) == 1
        assert hits[0].session_id == "01J9G7XK4P"

    def test_hit_has_platform(self, populated_store: Store):
        hits = list(search(populated_store, "hi from claude"))
        assert hits[0].platform == "claude"

    def test_hit_has_seq(self, populated_store: Store):
        hits = list(search(populated_store, "hi from claude"))
        assert hits[0].seq == 0

    def test_hit_has_type(self, populated_store: Store):
        hits = list(search(populated_store, "hi from claude"))
        assert hits[0].t == "user_message"

    def test_hit_has_snippet(self, populated_store: Store):
        hits = list(search(populated_store, "hi from claude"))
        assert isinstance(hits[0].snippet, str)
        assert len(hits[0].snippet) > 0

    def test_hit_is_dataclass(self, populated_store: Store):
        hits = list(search(populated_store, "hello"))
        h = hits[0]
        assert isinstance(h, Hit)

    def test_second_event_has_correct_seq(self, populated_store: Store):
        hits = list(search(populated_store, "hello user"))
        assert len(hits) == 1
        assert hits[0].seq == 1
        assert hits[0].t == "assistant_message"


# -- search: platform filter ---------------------------------------------------


class TestSearchFilterPlatform:
    def test_filter_by_platform_claude(self, populated_store: Store):
        hits = list(search(populated_store, "hi", platform="claude"))
        assert all(h.platform == "claude" for h in hits)
        assert len(hits) >= 1

    def test_filter_by_platform_cursor(self, populated_store: Store):
        hits = list(search(populated_store, "hi", platform="cursor"))
        assert len(hits) == 1
        assert hits[0].platform == "cursor"

    def test_filter_by_platform_no_matches(self, populated_store: Store):
        hits = list(search(populated_store, "hi", platform="codex"))
        assert hits == []

    def test_filter_platform_excludes_other(self, populated_store: Store):
        hits = list(search(populated_store, "hi from cursor", platform="claude"))
        assert hits == []


# -- search: cwd filter -------------------------------------------------------


class TestSearchFilterCwd:
    def test_filter_by_cwd(self, populated_store: Store):
        hits = list(search(populated_store, "hi", cwd="/proj/a"))
        assert all(h.session_id == "01J9G7XK4P" for h in hits)

    def test_filter_by_cwd_other(self, populated_store: Store):
        hits = list(search(populated_store, "hi", cwd="/proj/b"))
        assert len(hits) == 1
        assert hits[0].session_id == "02ABCDEF12"

    def test_filter_cwd_no_matches(self, populated_store: Store):
        hits = list(search(populated_store, "hi", cwd="/nonexistent"))
        assert hits == []


# -- search: combined filters --------------------------------------------------


class TestSearchCombinedFilters:
    def test_platform_and_cwd(self, populated_store: Store):
        hits = list(search(populated_store, "hi", platform="claude", cwd="/proj/a"))
        assert len(hits) >= 1
        assert all(h.platform == "claude" for h in hits)

    def test_platform_and_cwd_mismatch(self, populated_store: Store):
        # claude session has cwd=/proj/a, not /proj/b
        hits = list(search(populated_store, "hi", platform="claude", cwd="/proj/b"))
        assert hits == []


# -- search: empty store -------------------------------------------------------


class TestSearchEmptyStore:
    def test_empty_store_returns_empty(self, tmp_store: Store):
        assert list(search(tmp_store, "anything")) == []

    def test_empty_store_with_filters(self, tmp_store: Store):
        assert list(search(tmp_store, "x", platform="claude", cwd="/p")) == []


# -- search: returns iterator --------------------------------------------------


class TestSearchIterator:
    def test_returns_iterator(self, populated_store: Store):
        result = search(populated_store, "hi")
        assert hasattr(result, "__iter__")
        assert hasattr(result, "__next__")


# -- _snippet helper -----------------------------------------------------------


class TestSnippet:
    def test_basic_snippet(self):
        text = "the quick brown fox jumps over the lazy dog"
        result = _snippet(text, "fox", window=20)
        assert "fox" in result

    def test_snippet_adds_ellipsis_prefix(self):
        text = "a" * 100 + "NEEDLE" + "b" * 100
        result = _snippet(text, "NEEDLE", window=20)
        assert result.startswith("\u2026")

    def test_snippet_adds_ellipsis_suffix(self):
        text = "a" * 100 + "NEEDLE" + "b" * 100
        result = _snippet(text, "NEEDLE", window=20)
        assert result.endswith("\u2026")

    def test_snippet_no_ellipsis_at_start(self):
        text = "NEEDLE" + "b" * 100
        result = _snippet(text, "NEEDLE", window=20)
        assert not result.startswith("\u2026")

    def test_snippet_no_ellipsis_at_end(self):
        text = "a" * 10 + "NEEDLE"
        result = _snippet(text, "NEEDLE", window=80)
        assert not result.endswith("\u2026")

    def test_snippet_short_text_unchanged(self):
        text = "short"
        result = _snippet(text, "short", window=80)
        assert result == "short"

    def test_snippet_case_insensitive_match(self):
        text = "Hello World"
        result = _snippet(text, "hello", window=80)
        assert "Hello" in result

    def test_snippet_no_match_returns_head(self):
        text = "abcdef" * 20
        result = _snippet(text, "ZZZZZ", window=10)
        assert len(result) <= 10
        assert result == text[:10]

    def test_snippet_window_parameter(self):
        text = "x" * 200 + "NEEDLE" + "y" * 200
        result = _snippet(text, "NEEDLE", window=40)
        # Should contain NEEDLE plus surrounding context, bounded by window
        assert "NEEDLE" in result
        # Total should be roughly window + len(NEEDLE) + possible ellipses
        assert len(result) <= 40 + len("NEEDLE") + 2  # 2 for ellipsis chars


# -- _stringify helper ---------------------------------------------------------


class TestStringify:
    def test_dict_to_json(self):
        result = _stringify({"t": "msg", "data": "hello"})
        assert '"t"' in result
        assert '"hello"' in result

    def test_handles_non_serializable(self):
        # default=str should handle non-serializable types
        result = _stringify({"path": Path("/foo/bar")})
        assert "/foo/bar" in result

    def test_ensure_ascii_false(self):
        result = _stringify({"data": "unicode: \u00e9\u00e8\u00ea"})
        assert "\u00e9" in result

    def test_nested_structure(self):
        event = {"t": "x", "data": {"nested": [1, 2, 3]}}
        result = _stringify(event)
        assert "[1, 2, 3]" in result


# -- Hit dataclass -------------------------------------------------------------


class TestHitDataclass:
    def test_hit_creation(self):
        h = Hit(session_id="ABC", platform="claude", seq=0, t="msg", snippet="text")
        assert h.session_id == "ABC"
        assert h.platform == "claude"
        assert h.seq == 0
        assert h.t == "msg"
        assert h.snippet == "text"

    def test_hit_equality(self):
        h1 = Hit(session_id="A", platform="p", seq=0, t="t", snippet="s")
        h2 = Hit(session_id="A", platform="p", seq=0, t="t", snippet="s")
        assert h1 == h2

    def test_hit_inequality(self):
        h1 = Hit(session_id="A", platform="p", seq=0, t="t", snippet="s")
        h2 = Hit(session_id="B", platform="p", seq=0, t="t", snippet="s")
        assert h1 != h2
