from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from thirdeye.commands.usage import usage
from thirdeye.paths import session_dir, usage_db_path, usage_jsonl_path, usage_log_path


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point THIRDEYE_HOME at tmp_path and seed two sessions with usage data."""
    monkeypatch.setenv("THIRDEYE_HOME", str(tmp_path))

    def seed(platform: str, sid: str, rows: list[dict]) -> None:
        sd = session_dir(tmp_path, platform, sid)
        sd.mkdir(parents=True)
        with usage_jsonl_path(sd).open("w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")

    seed(
        "claude",
        "abc123",
        [
            {
                "session_id": "abc123",
                "seq": 0,
                "ts": "2026-05-10T00:00:00Z",
                "platform": "claude",
                "model": "claude-opus-4-7",
                "input_tokens": 100,
                "output_tokens": 10,
                "total_tokens": 110,
            },
            {
                "session_id": "abc123",
                "seq": 5,
                "ts": "2026-05-10T00:00:05Z",
                "platform": "claude",
                "model": "claude-opus-4-7",
                "input_tokens": 200,
                "output_tokens": 20,
                "total_tokens": 220,
            },
        ],
    )
    seed(
        "gemini",
        "def456",
        [
            {
                "session_id": "def456",
                "seq": 0,
                "ts": "2026-05-12T00:00:00Z",
                "platform": "gemini",
                "model": "gemini-3-flash-preview",
                "input_tokens": 9582,
                "output_tokens": 1,
                "total_tokens": 9748,
            },
        ],
    )
    return tmp_path


def test_rollup_default(home: Path) -> None:
    result = CliRunner().invoke(usage, [], catch_exceptions=False)
    assert result.exit_code == 0
    assert "abc123" in result.output
    assert "def456" in result.output
    assert "9,748" in result.output


def test_rollup_filter_by_platform(home: Path) -> None:
    result = CliRunner().invoke(usage, ["--platform", "gemini"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "def456" in result.output
    assert "abc123" not in result.output


def test_rollup_harness_alias(home: Path) -> None:
    result = CliRunner().invoke(usage, ["--harness", "claude"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "abc123" in result.output
    assert "def456" not in result.output


def test_rollup_json_output(home: Path) -> None:
    result = CliRunner().invoke(usage, ["--json"], catch_exceptions=False)
    assert result.exit_code == 0
    rows = [json.loads(line) for line in result.output.splitlines() if line.strip()]
    by_sid = {r["session_id"]: r for r in rows}
    assert by_sid["abc123"]["total_tokens"] == 330
    assert by_sid["def456"]["total_tokens"] == 9748


def test_rollup_top_n(home: Path) -> None:
    result = CliRunner().invoke(usage, ["--top", "1"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "def456" in result.output  # 9748 > 330
    assert "abc123" not in result.output


def test_per_session_view(home: Path) -> None:
    result = CliRunner().invoke(usage, ["abc"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "claude-opus-4-7" in result.output
    assert "110" in result.output and "220" in result.output


def test_per_session_json(home: Path) -> None:
    result = CliRunner().invoke(usage, ["abc", "--json"], catch_exceptions=False)
    assert result.exit_code == 0
    rows = [json.loads(line) for line in result.output.splitlines() if line.strip()]
    assert len(rows) == 2
    assert {r["seq"] for r in rows} == {0, 5}


def test_reindex_subcommand(home: Path) -> None:
    runner = CliRunner()
    runner.invoke(usage, [], catch_exceptions=False)  # populate
    assert usage_db_path(home).exists()

    result = runner.invoke(usage, ["reindex"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "Indexed" in result.output and "sessions" in result.output

    conn = sqlite3.connect(usage_db_path(home))
    assert conn.execute("SELECT COUNT(*) FROM usage").fetchone()[0] == 3


def test_errors_subcommand_no_log(home: Path) -> None:
    result = CliRunner().invoke(usage, ["errors"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "No usage errors" in result.output


def test_errors_subcommand_with_entries(home: Path) -> None:
    log = usage_log_path(home)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(
        json.dumps(
            {
                "ts": "2026-05-12T00:00:00Z",
                "level": "warn",
                "platform": "claude",
                "session_id": "abc123",
                "phase": "parse_transcript",
                "source_path": "/x",
                "error_class": "FileNotFoundError",
                "message": "gone",
                "traceback": "",
            }
        )
        + "\n"
    )
    runner = CliRunner()
    result = runner.invoke(usage, ["errors"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "parse_transcript" in result.output

    result = runner.invoke(usage, ["errors", "--json"], catch_exceptions=False)
    line = json.loads(result.output.strip())
    assert line["phase"] == "parse_transcript"

    result = runner.invoke(usage, ["errors", "--phase", "nothing-matches"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "No matching" in result.output
