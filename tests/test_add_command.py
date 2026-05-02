from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from atrace.cli import main
from atrace.platforms.claude.install import ClaudePlatform


# -- command registration ------------------------------------------------------


def test_add_appears_in_help():
    r = CliRunner().invoke(main, ["--help"])
    assert r.exit_code == 0
    assert "add" in r.output


def test_add_help_mentions_claude():
    r = CliRunner().invoke(main, ["add", "--help"])
    assert r.exit_code == 0
    assert "--claude" in r.output


def test_add_help_mentions_remove():
    r = CliRunner().invoke(main, ["add", "--help"])
    assert r.exit_code == 0
    assert "--remove" in r.output


# -- platform flag required ----------------------------------------------------


def test_add_requires_platform():
    r = CliRunner().invoke(main, ["add"])
    assert r.exit_code != 0
    assert "platform" in r.output.lower()


def test_add_remove_without_platform_fails():
    r = CliRunner().invoke(main, ["add", "--remove"])
    assert r.exit_code != 0
    assert "platform" in r.output.lower()


# -- install (--claude) -------------------------------------------------------


def test_add_claude_writes_settings(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    monkeypatch.setattr(
        "atrace.commands.add.ClaudePlatform",
        lambda: ClaudePlatform(settings_file=settings),
    )
    r = CliRunner().invoke(main, ["add", "--claude"])
    assert r.exit_code == 0, r.output
    assert "Installed" in r.output
    assert "Claude Code" in r.output
    data = json.loads(settings.read_text())
    assert "hooks" in data and len(data["hooks"]) >= 1


def test_add_claude_creates_settings_file(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    monkeypatch.setattr(
        "atrace.commands.add.ClaudePlatform",
        lambda: ClaudePlatform(settings_file=settings),
    )
    assert not settings.exists()
    CliRunner().invoke(main, ["add", "--claude"])
    assert settings.exists()


def test_add_claude_registers_all_hook_events(tmp_path: Path, monkeypatch):
    from atrace.platforms.claude.constants import HOOK_EVENTS

    settings = tmp_path / "settings.json"
    monkeypatch.setattr(
        "atrace.commands.add.ClaudePlatform",
        lambda: ClaudePlatform(settings_file=settings),
    )
    CliRunner().invoke(main, ["add", "--claude"])
    data = json.loads(settings.read_text())
    assert set(data["hooks"].keys()) == set(HOOK_EVENTS.keys())


def test_add_claude_idempotent(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    monkeypatch.setattr(
        "atrace.commands.add.ClaudePlatform",
        lambda: ClaudePlatform(settings_file=settings),
    )
    runner = CliRunner()
    runner.invoke(main, ["add", "--claude"])
    first = settings.read_text()
    runner.invoke(main, ["add", "--claude"])
    second = settings.read_text()
    assert first == second


def test_add_claude_preserves_existing_settings(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"theme": "dark"}))
    monkeypatch.setattr(
        "atrace.commands.add.ClaudePlatform",
        lambda: ClaudePlatform(settings_file=settings),
    )
    CliRunner().invoke(main, ["add", "--claude"])
    data = json.loads(settings.read_text())
    assert data["theme"] == "dark"
    assert "hooks" in data


# -- uninstall (--claude --remove) ---------------------------------------------


def test_add_claude_remove(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    monkeypatch.setattr(
        "atrace.commands.add.ClaudePlatform",
        lambda: ClaudePlatform(settings_file=settings),
    )
    runner = CliRunner()
    runner.invoke(main, ["add", "--claude"])
    r = runner.invoke(main, ["add", "--claude", "--remove"])
    assert r.exit_code == 0, r.output
    assert "Removed" in r.output
    assert "Claude Code" in r.output
    data = json.loads(settings.read_text())
    assert "hooks" not in data


def test_add_claude_remove_noop_when_not_installed(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    monkeypatch.setattr(
        "atrace.commands.add.ClaudePlatform",
        lambda: ClaudePlatform(settings_file=settings),
    )
    r = CliRunner().invoke(main, ["add", "--claude", "--remove"])
    assert r.exit_code == 0, r.output
    assert "Removed" in r.output


def test_add_claude_remove_preserves_other_settings(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"theme": "dark"}))
    monkeypatch.setattr(
        "atrace.commands.add.ClaudePlatform",
        lambda: ClaudePlatform(settings_file=settings),
    )
    runner = CliRunner()
    runner.invoke(main, ["add", "--claude"])
    runner.invoke(main, ["add", "--claude", "--remove"])
    data = json.loads(settings.read_text())
    assert data["theme"] == "dark"
    assert "hooks" not in data


def test_add_claude_reinstall_after_remove(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    monkeypatch.setattr(
        "atrace.commands.add.ClaudePlatform",
        lambda: ClaudePlatform(settings_file=settings),
    )
    runner = CliRunner()
    runner.invoke(main, ["add", "--claude"])
    first = json.loads(settings.read_text())
    runner.invoke(main, ["add", "--claude", "--remove"])
    runner.invoke(main, ["add", "--claude"])
    restored = json.loads(settings.read_text())
    assert first == restored


# -- output messages -----------------------------------------------------------


def test_add_install_output_contains_platform_name(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    monkeypatch.setattr(
        "atrace.commands.add.ClaudePlatform",
        lambda: ClaudePlatform(settings_file=settings),
    )
    r = CliRunner().invoke(main, ["add", "--claude"])
    assert r.exit_code == 0
    assert "Claude Code" in r.output


def test_add_remove_output_contains_platform_name(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    monkeypatch.setattr(
        "atrace.commands.add.ClaudePlatform",
        lambda: ClaudePlatform(settings_file=settings),
    )
    runner = CliRunner()
    runner.invoke(main, ["add", "--claude"])
    r = runner.invoke(main, ["add", "--claude", "--remove"])
    assert r.exit_code == 0
    assert "Claude Code" in r.output


# -- existing commands unaffected ----------------------------------------------


def test_existing_commands_still_registered():
    r = CliRunner().invoke(main, ["--help"])
    assert r.exit_code == 0
    for cmd in ["ingest", "list", "show", "events", "tail", "event", "search", "stats"]:
        assert cmd in r.output, f"command {cmd!r} missing from --help"


def test_ingest_still_works(tmp_path: Path):
    runner = CliRunner()
    env = {"ATRACE_HOME": str(tmp_path)}
    payload = json.dumps({"t": "msg", "data": "hi"}) + "\n"
    r = runner.invoke(
        main,
        ["ingest", "--platform", "claude", "--session-id", "REGR1"],
        input=payload,
        env=env,
    )
    assert r.exit_code == 0


# -- PLATFORMS dict correctness ------------------------------------------------


def test_platforms_dict_has_claude():
    from atrace.commands.add import PLATFORMS

    assert "claude" in PLATFORMS
    assert PLATFORMS["claude"] is ClaudePlatform


def test_platform_flag_value_maps_to_platforms_key():
    from atrace.commands.add import PLATFORMS

    for key, cls in PLATFORMS.items():
        instance = cls(settings_file=Path("/fake"))
        assert instance.name == key
