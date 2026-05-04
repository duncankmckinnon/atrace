from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from thirdeye.cli import main
from thirdeye.commands.add import PLATFORMS
from thirdeye.platforms.claude.install import ClaudePlatform

# -- command registration ------------------------------------------------------


def test_add_appears_in_help():
    r = CliRunner().invoke(main, ["--help"])
    assert r.exit_code == 0
    assert "add" in r.output


def test_remove_appears_in_help():
    r = CliRunner().invoke(main, ["--help"])
    assert r.exit_code == 0
    assert "remove" in r.output


def test_add_help_mentions_claude():
    r = CliRunner().invoke(main, ["add", "--help"])
    assert r.exit_code == 0
    assert "--claude" in r.output


def test_remove_help_mentions_claude():
    r = CliRunner().invoke(main, ["remove", "--help"])
    assert r.exit_code == 0
    assert "--claude" in r.output


# -- platform flag required ----------------------------------------------------


def test_add_requires_platform():
    r = CliRunner().invoke(main, ["add"])
    assert r.exit_code != 0
    assert "platform" in r.output.lower()


def test_remove_requires_platform():
    r = CliRunner().invoke(main, ["remove"])
    assert r.exit_code != 0
    assert "platform" in r.output.lower()


# -- install (add --claude) ----------------------------------------------------


def test_add_claude_writes_settings(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    monkeypatch.setitem(PLATFORMS, "claude", lambda: ClaudePlatform(settings_file=settings))
    r = CliRunner().invoke(main, ["add", "--claude"])
    assert r.exit_code == 0, r.output
    assert "Installed" in r.output
    assert "Claude Code" in r.output
    data = json.loads(settings.read_text())
    assert "hooks" in data and len(data["hooks"]) >= 1


def test_add_claude_creates_settings_file(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    monkeypatch.setitem(PLATFORMS, "claude", lambda: ClaudePlatform(settings_file=settings))
    assert not settings.exists()
    CliRunner().invoke(main, ["add", "--claude"])
    assert settings.exists()


def test_add_claude_registers_all_hook_events(tmp_path: Path, monkeypatch):
    from thirdeye.platforms.claude.constants import HOOK_EVENTS

    settings = tmp_path / "settings.json"
    monkeypatch.setitem(PLATFORMS, "claude", lambda: ClaudePlatform(settings_file=settings))
    CliRunner().invoke(main, ["add", "--claude"])
    data = json.loads(settings.read_text())
    assert set(data["hooks"].keys()) == set(HOOK_EVENTS.keys())


def test_add_claude_idempotent(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    monkeypatch.setitem(PLATFORMS, "claude", lambda: ClaudePlatform(settings_file=settings))
    runner = CliRunner()
    runner.invoke(main, ["add", "--claude"])
    first = settings.read_text()
    runner.invoke(main, ["add", "--claude"])
    second = settings.read_text()
    assert first == second


def test_add_claude_preserves_existing_settings(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"theme": "dark"}))
    monkeypatch.setitem(PLATFORMS, "claude", lambda: ClaudePlatform(settings_file=settings))
    CliRunner().invoke(main, ["add", "--claude"])
    data = json.loads(settings.read_text())
    assert data["theme"] == "dark"
    assert "hooks" in data


# -- uninstall (remove --claude) -----------------------------------------------


def test_remove_claude(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    monkeypatch.setitem(PLATFORMS, "claude", lambda: ClaudePlatform(settings_file=settings))
    runner = CliRunner()
    runner.invoke(main, ["add", "--claude"])
    r = runner.invoke(main, ["remove", "--claude"])
    assert r.exit_code == 0, r.output
    assert "Removed" in r.output
    assert "Claude Code" in r.output
    data = json.loads(settings.read_text())
    assert "hooks" not in data


def test_remove_claude_noop_when_not_installed(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    monkeypatch.setitem(PLATFORMS, "claude", lambda: ClaudePlatform(settings_file=settings))
    r = CliRunner().invoke(main, ["remove", "--claude"])
    assert r.exit_code == 0, r.output
    assert "Removed" in r.output


def test_remove_claude_preserves_other_settings(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"theme": "dark"}))
    monkeypatch.setitem(PLATFORMS, "claude", lambda: ClaudePlatform(settings_file=settings))
    runner = CliRunner()
    runner.invoke(main, ["add", "--claude"])
    runner.invoke(main, ["remove", "--claude"])
    data = json.loads(settings.read_text())
    assert data["theme"] == "dark"
    assert "hooks" not in data


def test_reinstall_after_remove(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    monkeypatch.setitem(PLATFORMS, "claude", lambda: ClaudePlatform(settings_file=settings))
    runner = CliRunner()
    runner.invoke(main, ["add", "--claude"])
    first = json.loads(settings.read_text())
    runner.invoke(main, ["remove", "--claude"])
    runner.invoke(main, ["add", "--claude"])
    restored = json.loads(settings.read_text())
    assert first == restored


# -- output messages -----------------------------------------------------------


def test_add_install_output_contains_platform_name(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    monkeypatch.setitem(PLATFORMS, "claude", lambda: ClaudePlatform(settings_file=settings))
    r = CliRunner().invoke(main, ["add", "--claude"])
    assert r.exit_code == 0
    assert "Claude Code" in r.output


def test_remove_output_contains_platform_name(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    monkeypatch.setitem(PLATFORMS, "claude", lambda: ClaudePlatform(settings_file=settings))
    runner = CliRunner()
    runner.invoke(main, ["add", "--claude"])
    r = runner.invoke(main, ["remove", "--claude"])
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
    env = {"THIRDEYE_HOME": str(tmp_path)}
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
    assert "claude" in PLATFORMS
    assert PLATFORMS["claude"] is ClaudePlatform


def test_platform_flag_value_maps_to_platforms_key():
    for key, cls in PLATFORMS.items():
        instance = cls(settings_file=Path("/fake"))
        assert instance.name == key


# -- implementation uses PLATFORMS dict ----------------------------------------


def test_add_uses_platforms_dict(monkeypatch):
    """The add command should dispatch via PLATFORMS[platform_flag](), not hardcode ClaudePlatform()."""
    from unittest.mock import MagicMock

    mock_platform = MagicMock()
    mock_platform.display_name = "Mock Platform"
    mock_cls = MagicMock(return_value=mock_platform)

    monkeypatch.setitem(PLATFORMS, "claude", mock_cls)
    r = CliRunner().invoke(main, ["add", "--claude"])
    assert r.exit_code == 0, r.output
    mock_cls.assert_called_once()
    mock_platform.install.assert_called_once()


def test_remove_uses_platforms_dict(monkeypatch):
    """The remove command should dispatch via PLATFORMS[platform_flag](), not hardcode ClaudePlatform()."""
    from unittest.mock import MagicMock

    mock_platform = MagicMock()
    mock_platform.display_name = "Mock Platform"
    mock_cls = MagicMock(return_value=mock_platform)

    monkeypatch.setitem(PLATFORMS, "claude", mock_cls)
    r = CliRunner().invoke(main, ["remove", "--claude"])
    assert r.exit_code == 0, r.output
    mock_cls.assert_called_once()
    mock_platform.uninstall.assert_called_once()


# -- hook command structure ----------------------------------------------------


def test_add_claude_hook_entries_have_command_type(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    monkeypatch.setitem(PLATFORMS, "claude", lambda: ClaudePlatform(settings_file=settings))
    CliRunner().invoke(main, ["add", "--claude"])
    data = json.loads(settings.read_text())
    for event_name, entries in data["hooks"].items():
        for entry in entries:
            for hook in entry["hooks"]:
                assert hook["type"] == "command", f"{event_name} hook missing type=command"
                assert "command" in hook, f"{event_name} hook missing command key"


def test_add_claude_hook_commands_contain_thirdeye(tmp_path: Path, monkeypatch):
    settings = tmp_path / "settings.json"
    monkeypatch.setitem(PLATFORMS, "claude", lambda: ClaudePlatform(settings_file=settings))
    CliRunner().invoke(main, ["add", "--claude"])
    data = json.loads(settings.read_text())
    for event_name, entries in data["hooks"].items():
        for entry in entries:
            for hook in entry["hooks"]:
                cmd = hook["command"]
                assert "thirdeye" in cmd, f"{event_name} command {cmd!r} missing 'thirdeye'"
