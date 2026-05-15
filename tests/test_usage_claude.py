from __future__ import annotations

import json
from pathlib import Path

import pytest

from thirdeye.paths import (
    session_dir,
    usage_jsonl_path,
    usage_log_path,
    usage_state_path,
)
from thirdeye.platforms.claude.usage import capture_usage_claude


FIXTURE = Path(__file__).parent / "fixtures" / "usage" / "claude_transcript.jsonl"


def test_capture_creates_rows_from_fixture(tmp_path: Path) -> None:
    rows = capture_usage_claude(
        thirdeye_home=tmp_path,
        session_id="abc123",
        transcript_path=str(FIXTURE),
        triggering_seq=5,
    )
    assert rows == 2
    jsonl = usage_jsonl_path(session_dir(tmp_path, "claude", "abc123"))
    lines = jsonl.read_text().strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["platform"] == "claude"
    assert first["seq"] == 5
    assert first["model"]
    assert first["input_tokens"] == 12450
    assert first["output_tokens"] == 187
    assert first["total_tokens"] == 12637


def test_capture_is_incremental(tmp_path: Path) -> None:
    """Re-running against the same transcript at the saved offset produces 0 new rows."""
    capture_usage_claude(
        thirdeye_home=tmp_path,
        session_id="abc",
        transcript_path=str(FIXTURE),
        triggering_seq=1,
    )
    sd = session_dir(tmp_path, "claude", "abc")
    state = json.loads(usage_state_path(sd).read_text())
    initial_offset = state["transcript_offset"]
    assert initial_offset > 0

    rows = capture_usage_claude(
        thirdeye_home=tmp_path,
        session_id="abc",
        transcript_path=str(FIXTURE),
        triggering_seq=2,
    )
    assert rows == 0
    state2 = json.loads(usage_state_path(sd).read_text())
    assert state2["transcript_offset"] == initial_offset


def test_capture_missing_transcript_logs_error(tmp_path: Path) -> None:
    rows = capture_usage_claude(
        thirdeye_home=tmp_path,
        session_id="abc",
        transcript_path="/nonexistent/path.jsonl",
        triggering_seq=1,
    )
    assert rows == 0
    log = usage_log_path(tmp_path)
    assert log.exists() and "open_source" in log.read_text()


def test_capture_with_no_transcript_path(tmp_path: Path) -> None:
    rows = capture_usage_claude(
        thirdeye_home=tmp_path,
        session_id="abc",
        transcript_path=None,
        triggering_seq=1,
    )
    assert rows == 0
    sd = session_dir(tmp_path, "claude", "abc")
    assert not usage_jsonl_path(sd).exists()


def test_capture_handles_corrupt_jsonl_lines(tmp_path: Path) -> None:
    transcript = tmp_path / "bad.jsonl"
    transcript.write_text(
        '{"type":"assistant","message":{"model":"claude-3","usage":{"input_tokens":10,"output_tokens":5}}}\n'
        "this is not json\n"
        '{"type":"assistant","message":{"model":"claude-3","usage":{"input_tokens":7,"output_tokens":3}}}\n'
    )
    rows = capture_usage_claude(
        thirdeye_home=tmp_path,
        session_id="abc",
        transcript_path=str(transcript),
        triggering_seq=10,
    )
    assert rows == 2


def test_capture_skips_non_assistant_frames(tmp_path: Path) -> None:
    transcript = tmp_path / "mixed.jsonl"
    transcript.write_text(
        '{"type":"user","message":{"role":"user","content":"hi"}}\n'
        '{"type":"assistant","message":{"model":"claude-3","usage":{"input_tokens":10,"output_tokens":5}}}\n'
        '{"type":"meta"}\n'
    )
    rows = capture_usage_claude(
        thirdeye_home=tmp_path,
        session_id="abc",
        transcript_path=str(transcript),
        triggering_seq=1,
    )
    assert rows == 1


def test_safe_capture_swallows_unexpected_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import thirdeye.platforms.claude.usage as mod
    monkeypatch.setattr(
        mod, "_extract_row", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("oops"))
    )
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(
        '{"type":"assistant","message":{"model":"c","usage":{"input_tokens":1,"output_tokens":1}}}\n'
    )
    result = capture_usage_claude(
        thirdeye_home=tmp_path,
        session_id="abc",
        transcript_path=str(transcript),
        triggering_seq=1,
    )
    assert result is None
    assert "RuntimeError" in usage_log_path(tmp_path).read_text()
