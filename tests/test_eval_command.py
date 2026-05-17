from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from thirdeye.commands.eval import eval_group
from thirdeye.eval.result import EvalResult
from thirdeye.eval.store import EvalStore
from thirdeye.paths import eval_def_path, session_dir


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("THIRDEYE_HOME", str(tmp_path))
    sd = session_dir(tmp_path, "claude", "abc123")
    sd.mkdir(parents=True)
    (sd / "meta.yaml").write_text(
        "schema_version: 2\nsession_id: abc123\nplatform: claude\n"
        "cwd: /x\nstarted_at: 2026-05-16T00:00:00Z\nended_at: null\n"
        "status: open\nevent_count: 1\nlast_seq: -1\nlast_ts: null\n"
    )
    # Custom definition
    cfg = eval_def_path(tmp_path, "test")
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        "name: test\ndescription: t\ndirective: |\n  evaluate\n"
        "default_agent: claude\noutput_schema: v1\n"
    )
    return tmp_path


def _seed_result(home: Path, sid: str, **overrides) -> EvalResult:
    base = dict(
        id="01J7XYZ",
        session_id=sid,
        definition="test",
        agent="claude",
        agent_model="",
        agent_session_id=None,
        started_at="2026-05-16T01:42:00Z",
        ended_at="2026-05-16T01:42:18Z",
        duration_ms=18000,
        verdict="warn",
        summary="seeded summary",
    )
    base.update(overrides)
    r = EvalResult(**base)
    EvalStore(session_dir(home, "claude", sid)).append(r)
    return r


def test_run_dispatch_invokes_runner(home: Path, monkeypatch):
    captured = {}

    def fake_run_eval(**kw):
        captured.update(kw)
        return EvalResult(
            id="X", session_id="abc123", definition="test", agent="claude",
            agent_model="", agent_session_id=None,
            started_at="t", ended_at="t", duration_ms=10,
            verdict="pass", summary="great",
        )
    monkeypatch.setattr("thirdeye.commands.eval.run_eval", fake_run_eval)
    result = CliRunner().invoke(eval_group, ["run", "abc", "--agent", "claude",
                                              "--using", "test"],
                                catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert "VERDICT: pass" in result.output
    assert captured["definition_name"] == "test"


def test_run_rejects_unknown_agent(home: Path):
    result = CliRunner().invoke(eval_group, ["run", "abc", "--agent", "not-real"])
    assert result.exit_code != 0
    assert "unknown agent" in result.output


def test_run_background_prints_job_id(home: Path, monkeypatch):
    monkeypatch.setattr(
        "thirdeye.commands.eval.run_eval_background",
        lambda **kw: "01J7BG"
    )
    result = CliRunner().invoke(eval_group, ["run", "abc", "--agent", "claude",
                                              "--using", "test", "--background"],
                                catch_exceptions=False)
    assert result.exit_code == 0
    assert "01J7BG" in result.output


def test_show_latest(home: Path):
    _seed_result(home, "abc123", summary="latest one")
    result = CliRunner().invoke(eval_group, ["show", "abc"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "latest one" in result.output


def test_show_by_id(home: Path):
    _seed_result(home, "abc123", id="ID-A", summary="first")
    _seed_result(home, "abc123", id="ID-B", summary="second")
    result = CliRunner().invoke(eval_group, ["show", "abc", "--id", "ID-A"],
                                catch_exceptions=False)
    assert result.exit_code == 0
    assert "first" in result.output
    assert "second" not in result.output


def test_show_no_results_errors(home: Path):
    result = CliRunner().invoke(eval_group, ["show", "abc"])
    assert result.exit_code != 0
    assert "no eval results" in result.output


def test_list_filters(home: Path):
    _seed_result(home, "abc123", id="A", verdict="pass", definition="test")
    _seed_result(home, "abc123", id="B", verdict="fail", definition="test")
    _seed_result(home, "abc123", id="C", verdict="pass", definition="other")
    result = CliRunner().invoke(
        eval_group, ["list", "--verdict", "pass", "--using", "test", "--json"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    ids = [json.loads(line)["id"] for line in result.output.splitlines() if line.strip()]
    assert ids == ["A"]


def test_status_no_jobs(home: Path):
    result = CliRunner().invoke(eval_group, ["status", "abc"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "No background eval jobs" in result.output


def test_status_orphan_detection(home: Path):
    sd = session_dir(home, "claude", "abc123")
    EvalStore(sd).write_job("J1", {
        "job_id": "J1", "session_id": "abc123", "using": "test",
        "agent": "claude", "status": "running", "started_at": "t",
        "pid": 99999999,  # almost certainly not running
    })
    result = CliRunner().invoke(eval_group, ["status", "abc"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "orphaned" in result.output


def test_def_list_shows_shipped(home: Path):
    result = CliRunner().invoke(eval_group, ["def", "list"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "default" in result.output
    assert "(shipped)" in result.output


def test_def_show_default(home: Path):
    result = CliRunner().invoke(eval_group, ["def", "show", "default"],
                                catch_exceptions=False)
    assert result.exit_code == 0
    assert "name: default" in result.output


def test_def_create_with_directive(home: Path):
    result = CliRunner().invoke(
        eval_group,
        ["def", "create", "my-eval", "--directive", "evaluate X",
         "--description", "custom"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "Created" in result.output
    # Verify it loads
    result2 = CliRunner().invoke(eval_group, ["def", "show", "my-eval"],
                                 catch_exceptions=False)
    assert "evaluate X" in result2.output


def test_def_create_rejects_no_source(home: Path):
    result = CliRunner().invoke(eval_group, ["def", "create", "bad"])
    assert result.exit_code != 0
    assert "exactly one of" in result.output


def test_def_create_rejects_multiple_sources(home: Path):
    result = CliRunner().invoke(
        eval_group,
        ["def", "create", "bad", "--directive", "a", "--from", "default"],
    )
    assert result.exit_code != 0


def test_def_rm_shipped_allows_restore(home: Path):
    # Materialize shipped 'default'
    CliRunner().invoke(eval_group, ["def", "show", "default"], catch_exceptions=False)
    result = CliRunner().invoke(eval_group, ["def", "rm", "default"],
                                catch_exceptions=False)
    assert result.exit_code == 0
    assert "shipped version restored" in result.output


def test_def_rm_missing_errors(home: Path):
    result = CliRunner().invoke(eval_group, ["def", "rm", "nonexistent"])
    assert result.exit_code != 0
