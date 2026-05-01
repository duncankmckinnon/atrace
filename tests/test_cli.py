from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from atrace.cli import main


def _runner_with_home(tmp_path: Path) -> tuple[CliRunner, dict]:
    return CliRunner(), {"ATRACE_HOME": str(tmp_path)}


# -- help / version -----------------------------------------------------------


def test_help(tmp_path: Path):
    runner, env = _runner_with_home(tmp_path)
    r = runner.invoke(main, ["--help"], env=env)
    assert r.exit_code == 0
    assert "atrace" in r.output.lower()


def test_version(tmp_path: Path):
    runner, env = _runner_with_home(tmp_path)
    r = runner.invoke(main, ["--version"], env=env)
    assert r.exit_code == 0
    assert "0.1.0" in r.output


def test_ingest_help(tmp_path: Path):
    runner, env = _runner_with_home(tmp_path)
    r = runner.invoke(main, ["ingest", "--help"], env=env)
    assert r.exit_code == 0
    assert "--platform" in r.output
    assert "--session-id" in r.output
    assert "--cwd" in r.output


# -- ingest basic flow --------------------------------------------------------


def test_ingest_writes_session(tmp_path: Path):
    runner, env = _runner_with_home(tmp_path)
    payload = (
        json.dumps({"t": "user_message", "data": "hi"}) + "\n"
        + json.dumps({"t": "assistant_message", "data": "hello"}) + "\n"
    )
    r = runner.invoke(
        main,
        ["ingest", "--platform", "claude", "--session-id", "01J9G7XK4P", "--cwd", "/p"],
        input=payload,
        env=env,
    )
    assert r.exit_code == 0, r.output

    sd = tmp_path / "traces" / "claude" / "01J9G7XK4P"
    assert (sd / "events.alog").exists()
    assert (sd / "events.idx").stat().st_size == 16  # 2 events * 8 bytes each
    assert (sd / "meta.yaml").exists()


def test_ingest_event_count_in_stderr(tmp_path: Path):
    runner, env = _runner_with_home(tmp_path)
    payload = json.dumps({"t": "msg", "data": "hi"}) + "\n"
    r = runner.invoke(
        main,
        ["ingest", "--platform", "claude", "--session-id", "SID1"],
        input=payload,
        env=env,
    )
    assert r.exit_code == 0
    # stderr should contain the session id and event count
    assert "SID1" in (r.output + getattr(r, "stderr", ""))
    assert "1 events" in (r.output + getattr(r, "stderr", ""))


def test_ingest_prints_session_id_to_stdout(tmp_path: Path):
    runner, env = _runner_with_home(tmp_path)
    payload = json.dumps({"t": "msg"}) + "\n"
    r = runner.invoke(
        main,
        ["ingest", "--platform", "claude", "--session-id", "MYSID"],
        input=payload,
        env=env,
    )
    assert r.exit_code == 0
    # The last line of stdout should be the session ID alone
    assert "MYSID" in r.output


# -- session-id auto-generation -----------------------------------------------


def test_ingest_generates_session_id_when_omitted(tmp_path: Path):
    runner, env = _runner_with_home(tmp_path)
    payload = json.dumps({"t": "msg", "data": "x"}) + "\n"
    r = runner.invoke(
        main,
        ["ingest", "--platform", "claude"],
        input=payload,
        env=env,
    )
    assert r.exit_code == 0
    # Output should contain a ULID (26 chars, alphanumeric)
    lines = r.output.strip().splitlines()
    generated_id = lines[-1].strip()
    assert len(generated_id) == 26
    # Session dir should exist under the generated ID
    sd = tmp_path / "traces" / "claude" / generated_id
    assert sd.is_dir()


# -- cwd default --------------------------------------------------------------


def test_ingest_cwd_defaults_to_dot(tmp_path: Path):
    runner, env = _runner_with_home(tmp_path)
    payload = json.dumps({"t": "msg"}) + "\n"
    r = runner.invoke(
        main,
        ["ingest", "--platform", "claude", "--session-id", "CWD1"],
        input=payload,
        env=env,
    )
    assert r.exit_code == 0
    # meta.yaml should record cwd as "."
    import yaml
    meta = yaml.safe_load((tmp_path / "traces" / "claude" / "CWD1" / "meta.yaml").read_text())
    assert meta["cwd"] == "."


def test_ingest_cwd_explicit(tmp_path: Path):
    runner, env = _runner_with_home(tmp_path)
    payload = json.dumps({"t": "msg"}) + "\n"
    r = runner.invoke(
        main,
        ["ingest", "--platform", "claude", "--session-id", "CWD2", "--cwd", "/my/project"],
        input=payload,
        env=env,
    )
    assert r.exit_code == 0
    import yaml
    meta = yaml.safe_load((tmp_path / "traces" / "claude" / "CWD2" / "meta.yaml").read_text())
    assert meta["cwd"] == "/my/project"


# -- blank lines / empty input ------------------------------------------------


def test_ingest_skips_blank_lines(tmp_path: Path):
    runner, env = _runner_with_home(tmp_path)
    payload = (
        "\n"
        + json.dumps({"t": "msg", "data": "one"}) + "\n"
        + "\n"
        + "   \n"
        + json.dumps({"t": "msg", "data": "two"}) + "\n"
        + "\n"
    )
    r = runner.invoke(
        main,
        ["ingest", "--platform", "claude", "--session-id", "BLANK1"],
        input=payload,
        env=env,
    )
    assert r.exit_code == 0
    # Only 2 real events, blank lines skipped
    sd = tmp_path / "traces" / "claude" / "BLANK1"
    assert (sd / "events.idx").stat().st_size == 16  # 2 * 8


def test_ingest_empty_stdin(tmp_path: Path):
    runner, env = _runner_with_home(tmp_path)
    r = runner.invoke(
        main,
        ["ingest", "--platform", "claude", "--session-id", "EMPTY1"],
        input="",
        env=env,
    )
    assert r.exit_code == 0
    # 0 events written
    assert "0 events" in (r.output + getattr(r, "stderr", ""))


# -- event field defaults -----------------------------------------------------


def test_ingest_defaults_t_to_event(tmp_path: Path):
    """When `t` is absent from the JSON line, it defaults to "event"."""
    runner, env = _runner_with_home(tmp_path)
    payload = json.dumps({"data": "something"}) + "\n"
    r = runner.invoke(
        main,
        ["ingest", "--platform", "claude", "--session-id", "TDEF1"],
        input=payload,
        env=env,
    )
    assert r.exit_code == 0
    # Verify a single event was written
    sd = tmp_path / "traces" / "claude" / "TDEF1"
    assert (sd / "events.idx").stat().st_size == 8  # 1 event


def test_ingest_data_none_when_absent(tmp_path: Path):
    """When `data` is absent from the JSON line, data=None is passed to append."""
    runner, env = _runner_with_home(tmp_path)
    payload = json.dumps({"t": "ping"}) + "\n"
    r = runner.invoke(
        main,
        ["ingest", "--platform", "claude", "--session-id", "DNIL1"],
        input=payload,
        env=env,
    )
    assert r.exit_code == 0
    sd = tmp_path / "traces" / "claude" / "DNIL1"
    assert (sd / "events.idx").stat().st_size == 8


# -- platform required --------------------------------------------------------


def test_ingest_requires_platform(tmp_path: Path):
    runner, env = _runner_with_home(tmp_path)
    payload = json.dumps({"t": "msg"}) + "\n"
    r = runner.invoke(
        main,
        ["ingest"],
        input=payload,
        env=env,
    )
    assert r.exit_code != 0
    assert "platform" in r.output.lower() or "required" in r.output.lower()


# -- multiple events ----------------------------------------------------------


def test_ingest_many_events(tmp_path: Path):
    runner, env = _runner_with_home(tmp_path)
    n = 50
    lines = [json.dumps({"t": f"evt_{i}", "data": {"n": i}}) for i in range(n)]
    payload = "\n".join(lines) + "\n"
    r = runner.invoke(
        main,
        ["ingest", "--platform", "cursor", "--session-id", "MANY1"],
        input=payload,
        env=env,
    )
    assert r.exit_code == 0
    sd = tmp_path / "traces" / "cursor" / "MANY1"
    assert (sd / "events.idx").stat().st_size == n * 8


# -- session closed after ingest ----------------------------------------------


def test_ingest_closes_session(tmp_path: Path):
    runner, env = _runner_with_home(tmp_path)
    payload = json.dumps({"t": "msg", "data": "hi"}) + "\n"
    r = runner.invoke(
        main,
        ["ingest", "--platform", "claude", "--session-id", "CLOSE1"],
        input=payload,
        env=env,
    )
    assert r.exit_code == 0
    import yaml
    meta = yaml.safe_load(
        (tmp_path / "traces" / "claude" / "CLOSE1" / "meta.yaml").read_text()
    )
    assert meta["status"] == "closed"


# -- events are readable after ingest -----------------------------------------


def test_ingest_events_readable(tmp_path: Path):
    """After ingest, the stored events should be readable via SessionReader."""
    runner, env = _runner_with_home(tmp_path)
    payload = (
        json.dumps({"t": "user_message", "data": "hello"}) + "\n"
        + json.dumps({"t": "assistant_message", "data": "world"}) + "\n"
    )
    r = runner.invoke(
        main,
        ["ingest", "--platform", "claude", "--session-id", "READ1", "--cwd", "/proj"],
        input=payload,
        env=env,
    )
    assert r.exit_code == 0

    from atrace.config import Config
    from atrace.store import Store

    store = Store(Config(root=tmp_path))
    reader = store.reader("READ1")
    events = list(reader.iter_events())
    assert len(events) == 2
    assert events[0]["t"] == "user_message"
    assert events[0]["data"] == "hello"
    assert events[1]["t"] == "assistant_message"
    assert events[1]["data"] == "world"


# -- different platforms -------------------------------------------------------


def test_ingest_different_platforms(tmp_path: Path):
    runner, env = _runner_with_home(tmp_path)
    for platform in ["claude", "cursor", "codex"]:
        payload = json.dumps({"t": "msg", "data": platform}) + "\n"
        r = runner.invoke(
            main,
            ["ingest", "--platform", platform, "--session-id", f"SID_{platform}"],
            input=payload,
            env=env,
        )
        assert r.exit_code == 0, f"failed for {platform}: {r.output}"
    # All three session dirs exist
    for platform in ["claude", "cursor", "codex"]:
        assert (tmp_path / "traces" / platform / f"SID_{platform}").is_dir()


# -- invalid JSON input -------------------------------------------------------


def test_ingest_invalid_json_fails(tmp_path: Path):
    """Invalid JSON on stdin should cause a non-zero exit."""
    runner, env = _runner_with_home(tmp_path)
    r = runner.invoke(
        main,
        ["ingest", "--platform", "claude", "--session-id", "BADJSON"],
        input="not valid json\n",
        env=env,
    )
    assert r.exit_code != 0


def test_ingest_partial_valid_json_stops_at_bad_line(tmp_path: Path):
    """If good lines precede a bad line, the command should fail on the bad line."""
    runner, env = _runner_with_home(tmp_path)
    payload = (
        json.dumps({"t": "ok", "data": "fine"}) + "\n"
        + "BAD LINE\n"
    )
    r = runner.invoke(
        main,
        ["ingest", "--platform", "claude", "--session-id", "PARTIAL1"],
        input=payload,
        env=env,
    )
    assert r.exit_code != 0


# -- event data roundtrip with defaults ----------------------------------------


def test_ingest_default_t_value_readable(tmp_path: Path):
    """When t is omitted, the stored event should have t='event'."""
    runner, env = _runner_with_home(tmp_path)
    payload = json.dumps({"data": "no_type"}) + "\n"
    r = runner.invoke(
        main,
        ["ingest", "--platform", "claude", "--session-id", "TROUND"],
        input=payload,
        env=env,
    )
    assert r.exit_code == 0

    from atrace.config import Config
    from atrace.store import Store

    store = Store(Config(root=tmp_path))
    reader = store.reader("TROUND")
    events = list(reader.iter_events())
    assert len(events) == 1
    assert events[0]["t"] == "event"
    assert events[0]["data"] == "no_type"


def test_ingest_data_none_roundtrip(tmp_path: Path):
    """When data is omitted, stored event should not have a data key (or have None)."""
    runner, env = _runner_with_home(tmp_path)
    payload = json.dumps({"t": "ping"}) + "\n"
    r = runner.invoke(
        main,
        ["ingest", "--platform", "claude", "--session-id", "DROUND"],
        input=payload,
        env=env,
    )
    assert r.exit_code == 0

    from atrace.config import Config
    from atrace.store import Store

    store = Store(Config(root=tmp_path))
    reader = store.reader("DROUND")
    events = list(reader.iter_events())
    assert len(events) == 1
    assert events[0]["t"] == "ping"
    # data=None means the key is either absent or None
    assert events[0].get("data") is None


# -- only-blank-lines input ---------------------------------------------------


def test_ingest_only_blank_lines(tmp_path: Path):
    """Stdin with only blank/whitespace lines should write 0 events."""
    runner, env = _runner_with_home(tmp_path)
    r = runner.invoke(
        main,
        ["ingest", "--platform", "claude", "--session-id", "BLANKS"],
        input="\n\n  \n\t\n",
        env=env,
    )
    assert r.exit_code == 0
    assert "0 events" in (r.output + getattr(r, "stderr", ""))


# -- complex data types -------------------------------------------------------


def test_ingest_complex_data(tmp_path: Path):
    """Events with nested dicts, lists, and various types should roundtrip."""
    runner, env = _runner_with_home(tmp_path)
    complex_data = {
        "nested": {"a": [1, 2, 3]},
        "flag": True,
        "count": 42,
        "label": None,
    }
    payload = json.dumps({"t": "complex", "data": complex_data}) + "\n"
    r = runner.invoke(
        main,
        ["ingest", "--platform", "claude", "--session-id", "CPLX1"],
        input=payload,
        env=env,
    )
    assert r.exit_code == 0

    from atrace.config import Config
    from atrace.store import Store

    store = Store(Config(root=tmp_path))
    reader = store.reader("CPLX1")
    events = list(reader.iter_events())
    assert len(events) == 1
    assert events[0]["data"] == complex_data


# -- meta.yaml platform field --------------------------------------------------


def test_ingest_meta_records_platform(tmp_path: Path):
    """meta.yaml should record the platform passed via --platform."""
    runner, env = _runner_with_home(tmp_path)
    payload = json.dumps({"t": "msg"}) + "\n"
    r = runner.invoke(
        main,
        ["ingest", "--platform", "gemini", "--session-id", "PLAT1"],
        input=payload,
        env=env,
    )
    assert r.exit_code == 0
    import yaml
    meta = yaml.safe_load(
        (tmp_path / "traces" / "gemini" / "PLAT1" / "meta.yaml").read_text()
    )
    assert meta["platform"] == "gemini"
    assert meta["session_id"] == "PLAT1"
