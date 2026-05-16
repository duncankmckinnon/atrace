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


def test_reindex_targets_one_session(home: Path) -> None:
    """`reindex <prefix>` must wipe + rebuild only the matched session."""
    runner = CliRunner()
    runner.invoke(usage, [], catch_exceptions=False)  # populate index

    db = usage_db_path(home)
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM usage").fetchone()[0] == 3
    conn.close()

    result = runner.invoke(usage, ["reindex", "abc"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "from 1 session" in result.output

    # abc123 rows are still present (re-indexed), def456 untouched
    conn = sqlite3.connect(db)
    rows = conn.execute("SELECT session_id, seq FROM usage ORDER BY session_id, seq").fetchall()
    assert rows == [("abc123", 0), ("abc123", 5), ("def456", 0)]
    # usage_sync should only have an entry for the rebuilt session and the
    # previously-synced def456
    sync_ids = {r[0] for r in conn.execute("SELECT session_id FROM usage_sync").fetchall()}
    assert "abc123" in sync_ids
    conn.close()


def test_reindex_unknown_prefix_errors(home: Path) -> None:
    """An unknown prefix must surface a clean ClickException, not crash."""
    runner = CliRunner()
    result = runner.invoke(usage, ["reindex", "zzz-nonexistent"])
    assert result.exit_code != 0
    # ClickException renders to stderr; click.testing merges by default
    assert "zzz-nonexistent" in result.output or "no session" in result.output.lower()


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


def _write_log(home: Path, entries: list[dict]) -> None:
    """Append `entries` to <home>/logs/usage-errors.jsonl, creating dirs."""
    log = usage_log_path(home)
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def _entry(**overrides) -> dict:
    base = {
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
    base.update(overrides)
    return base


def test_errors_filter_by_platform(home: Path) -> None:
    _write_log(
        home,
        [
            _entry(platform="claude", phase="parse_transcript"),
            _entry(platform="gemini", phase="extract_usage", session_id="def456"),
            _entry(platform="codex", phase="parse_rollout", session_id="ghi789"),
        ],
    )
    runner = CliRunner()
    result = runner.invoke(
        usage, ["errors", "--platform", "gemini", "--json"], catch_exceptions=False
    )
    assert result.exit_code == 0
    lines = [json.loads(l) for l in result.output.splitlines() if l.strip()]
    assert len(lines) == 1
    assert lines[0]["platform"] == "gemini"
    assert lines[0]["session_id"] == "def456"


def test_errors_filter_by_since(home: Path) -> None:
    _write_log(
        home,
        [
            _entry(ts="2026-05-01T00:00:00Z", phase="old"),
            _entry(ts="2026-05-10T00:00:00Z", phase="mid"),
            _entry(ts="2026-05-20T00:00:00Z", phase="new"),
        ],
    )
    runner = CliRunner()
    result = runner.invoke(
        usage, ["errors", "--since", "2026-05-09", "--json"], catch_exceptions=False
    )
    assert result.exit_code == 0
    phases = {json.loads(l)["phase"] for l in result.output.splitlines() if l.strip()}
    assert phases == {"mid", "new"}


def test_errors_filter_by_until(home: Path) -> None:
    _write_log(
        home,
        [
            _entry(ts="2026-05-01T00:00:00Z", phase="old"),
            _entry(ts="2026-05-10T00:00:00Z", phase="mid"),
            _entry(ts="2026-05-20T00:00:00Z", phase="new"),
        ],
    )
    runner = CliRunner()
    result = runner.invoke(
        usage, ["errors", "--until", "2026-05-15", "--json"], catch_exceptions=False
    )
    assert result.exit_code == 0
    phases = {json.loads(l)["phase"] for l in result.output.splitlines() if l.strip()}
    assert phases == {"old", "mid"}


def test_errors_combined_since_and_until(home: Path) -> None:
    _write_log(
        home,
        [
            _entry(ts="2026-05-01T00:00:00Z", phase="old"),
            _entry(ts="2026-05-10T00:00:00Z", phase="mid"),
            _entry(ts="2026-05-20T00:00:00Z", phase="new"),
        ],
    )
    runner = CliRunner()
    result = runner.invoke(
        usage,
        ["errors", "--since", "2026-05-05", "--until", "2026-05-15", "--json"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    phases = {json.loads(l)["phase"] for l in result.output.splitlines() if l.strip()}
    assert phases == {"mid"}


def test_errors_skips_malformed_jsonl_lines(home: Path) -> None:
    """A malformed line in usage-errors.jsonl must be silently skipped."""
    log = usage_log_path(home)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(
        json.dumps(_entry(phase="first")) + "\n"
        "this is not valid json\n"
        "\n"  # blank line
         + json.dumps(_entry(phase="second")) + "\n"
    )
    runner = CliRunner()
    result = runner.invoke(usage, ["errors", "--json"], catch_exceptions=False)
    assert result.exit_code == 0
    phases = [json.loads(l)["phase"] for l in result.output.splitlines() if l.strip()]
    assert phases == ["first", "second"]


def test_errors_skips_entries_with_unparseable_ts_when_time_filter_set(
    home: Path,
) -> None:
    """Under --since/--until, entries with bad ts are dropped, not crashed on."""
    _write_log(
        home,
        [
            _entry(ts="not-a-timestamp", phase="bad_ts"),
            _entry(ts="2026-05-10T00:00:00Z", phase="good_ts"),
        ],
    )
    runner = CliRunner()
    result = runner.invoke(
        usage, ["errors", "--since", "2026-05-01", "--json"], catch_exceptions=False
    )
    assert result.exit_code == 0
    phases = {json.loads(l)["phase"] for l in result.output.splitlines() if l.strip()}
    assert phases == {"good_ts"}


def test_errors_combined_filters(home: Path) -> None:
    """--platform + --phase + --since AND together."""
    _write_log(
        home,
        [
            _entry(platform="claude", phase="parse_transcript", ts="2026-05-01T00:00:00Z"),
            _entry(platform="claude", phase="parse_transcript", ts="2026-05-10T00:00:00Z"),
            _entry(platform="claude", phase="index_sync", ts="2026-05-10T00:00:00Z"),
            _entry(platform="gemini", phase="parse_transcript", ts="2026-05-10T00:00:00Z"),
        ],
    )
    runner = CliRunner()
    result = runner.invoke(
        usage,
        [
            "errors",
            "--platform",
            "claude",
            "--phase",
            "parse_transcript",
            "--since",
            "2026-05-05",
            "--json",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    lines = [json.loads(l) for l in result.output.splitlines() if l.strip()]
    assert len(lines) == 1
    e = lines[0]
    assert e["platform"] == "claude"
    assert e["phase"] == "parse_transcript"
    assert e["ts"] == "2026-05-10T00:00:00Z"


def test_errors_respects_tail_n(home: Path) -> None:
    """-n caps to the last N matching entries (after filtering)."""
    _write_log(home, [_entry(phase=f"p{i}") for i in range(5)])
    runner = CliRunner()
    result = runner.invoke(usage, ["errors", "-n", "2", "--json"], catch_exceptions=False)
    assert result.exit_code == 0
    phases = [json.loads(l)["phase"] for l in result.output.splitlines() if l.strip()]
    # Last two appended
    assert phases == ["p3", "p4"]
