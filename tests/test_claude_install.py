from __future__ import annotations

import json
from pathlib import Path

import pytest

from atrace.platforms.claude.constants import HOOK_EVENTS
from atrace.platforms.claude.install import ClaudePlatform


class TestClaudePlatformAttributes:
    def test_name_is_claude(self):
        p = ClaudePlatform(settings_file=Path("/fake/settings.json"))
        assert p.name == "claude"

    def test_display_name(self):
        p = ClaudePlatform(settings_file=Path("/fake/settings.json"))
        assert p.display_name == "Claude Code"

    def test_is_platform_subclass(self):
        from atrace.platforms.base import Platform

        assert issubclass(ClaudePlatform, Platform)


class TestInstallFreshFile:
    def test_writes_all_hook_events(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        ClaudePlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        assert set(settings["hooks"].keys()) == set(HOOK_EVENTS.keys())

    def test_creates_parent_dir(self, tmp_path: Path):
        settings_file = tmp_path / "nested" / "deeper" / "settings.json"
        ClaudePlatform(settings_file=settings_file).install()
        assert settings_file.exists()

    def test_sets_command_type(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        ClaudePlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        for entries in settings["hooks"].values():
            for entry in entries:
                for h in entry["hooks"]:
                    assert h["type"] == "command"
                    assert "command" in h and isinstance(h["command"], str)

    def test_each_event_has_one_entry(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        ClaudePlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        for event, entries in settings["hooks"].items():
            assert len(entries) == 1, f"expected 1 entry for {event}"

    def test_command_contains_script_name(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        ClaudePlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        for event, script in HOOK_EVENTS.items():
            cmds = [
                h["command"]
                for entry in settings["hooks"][event]
                for h in entry["hooks"]
            ]
            assert any(script in c for c in cmds), f"{script} not in commands for {event}"

    def test_output_is_valid_json(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        ClaudePlatform(settings_file=settings_file).install()
        json.loads(settings_file.read_text())

    def test_file_ends_with_newline(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        ClaudePlatform(settings_file=settings_file).install()
        assert settings_file.read_text().endswith("\n")


class TestInstallIdempotent:
    def test_no_duplicate_commands(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        p = ClaudePlatform(settings_file=settings_file)
        p.install()
        p.install()
        settings = json.loads(settings_file.read_text())
        for entries in settings["hooks"].values():
            commands = [h["command"] for entry in entries for h in entry["hooks"]]
            assert len(commands) == len(set(commands))

    def test_no_duplicate_entries(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        p = ClaudePlatform(settings_file=settings_file)
        p.install()
        p.install()
        p.install()
        settings = json.loads(settings_file.read_text())
        for event, entries in settings["hooks"].items():
            assert len(entries) == 1, f"expected 1 entry for {event} after 3 installs"

    def test_content_identical_after_double_install(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        p = ClaudePlatform(settings_file=settings_file)
        p.install()
        first = settings_file.read_text()
        p.install()
        second = settings_file.read_text()
        assert first == second


class TestInstallPreservesExisting:
    def test_preserves_existing_settings(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"theme": "dark", "env": {"FOO": "bar"}}))
        ClaudePlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        assert settings["theme"] == "dark"
        assert settings["env"] == {"FOO": "bar"}
        assert "hooks" in settings

    def test_preserves_unrelated_hooks(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"type": "command", "command": "/some/other/tool"}]}
                ]
            }
        }))
        ClaudePlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        cmds = [
            h["command"]
            for entry in settings["hooks"]["SessionStart"]
            for h in entry["hooks"]
        ]
        assert "/some/other/tool" in cmds
        assert any("atrace-claude-session-start" in c for c in cmds)

    def test_preserves_hooks_for_unknown_events(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({
            "hooks": {
                "CustomEvent": [
                    {"hooks": [{"type": "command", "command": "/custom/hook"}]}
                ]
            }
        }))
        ClaudePlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        assert "CustomEvent" in settings["hooks"]
        cmds = [
            h["command"]
            for entry in settings["hooks"]["CustomEvent"]
            for h in entry["hooks"]
        ]
        assert "/custom/hook" in cmds


class TestInstallEdgeCases:
    def test_handles_empty_file(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text("")
        ClaudePlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        assert set(settings["hooks"].keys()) == set(HOOK_EVENTS.keys())

    def test_handles_malformed_json(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text("{invalid json")
        ClaudePlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        assert set(settings["hooks"].keys()) == set(HOOK_EVENTS.keys())

    def test_handles_empty_hooks_dict(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"hooks": {}}))
        ClaudePlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        assert set(settings["hooks"].keys()) == set(HOOK_EVENTS.keys())

    def test_handles_empty_event_list(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({
            "hooks": {"SessionStart": []}
        }))
        ClaudePlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        assert len(settings["hooks"]["SessionStart"]) == 1


class TestUninstallRemovesHooks:
    def test_removes_all_our_hooks(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        p = ClaudePlatform(settings_file=settings_file)
        p.install()
        p.uninstall()
        settings = json.loads(settings_file.read_text())
        assert "hooks" not in settings

    def test_drops_empty_hooks_key(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        p = ClaudePlatform(settings_file=settings_file)
        p.install()
        p.uninstall()
        settings = json.loads(settings_file.read_text())
        assert "hooks" not in settings

    def test_removes_only_our_hooks(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"type": "command", "command": "/some/other/tool"}]}
                ]
            }
        }))
        p = ClaudePlatform(settings_file=settings_file)
        p.install()
        p.uninstall()
        settings = json.loads(settings_file.read_text())
        cmds = [
            h["command"]
            for entry in settings["hooks"]["SessionStart"]
            for h in entry["hooks"]
        ]
        assert "/some/other/tool" in cmds
        assert not any("atrace-claude-session-start" in c for c in cmds)

    def test_preserves_other_settings_on_uninstall(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"theme": "dark"}))
        p = ClaudePlatform(settings_file=settings_file)
        p.install()
        p.uninstall()
        settings = json.loads(settings_file.read_text())
        assert settings["theme"] == "dark"

    def test_preserves_hooks_for_unknown_events_on_uninstall(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({
            "hooks": {
                "CustomEvent": [
                    {"hooks": [{"type": "command", "command": "/custom/hook"}]}
                ]
            }
        }))
        p = ClaudePlatform(settings_file=settings_file)
        p.install()
        p.uninstall()
        settings = json.loads(settings_file.read_text())
        assert "CustomEvent" in settings["hooks"]
        cmds = [
            h["command"]
            for entry in settings["hooks"]["CustomEvent"]
            for h in entry["hooks"]
        ]
        assert "/custom/hook" in cmds


class TestUninstallEdgeCases:
    def test_no_settings_file_is_noop(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        ClaudePlatform(settings_file=settings_file).uninstall()
        assert not settings_file.exists()

    def test_no_hooks_key_is_noop(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"theme": "dark"}))
        ClaudePlatform(settings_file=settings_file).uninstall()
        settings = json.loads(settings_file.read_text())
        assert settings == {"theme": "dark"}

    def test_uninstall_idempotent(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        p = ClaudePlatform(settings_file=settings_file)
        p.install()
        p.uninstall()
        p.uninstall()
        settings = json.loads(settings_file.read_text())
        assert "hooks" not in settings

    def test_uninstall_then_install_restores(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        p = ClaudePlatform(settings_file=settings_file)
        p.install()
        first = json.loads(settings_file.read_text())
        p.uninstall()
        p.install()
        restored = json.loads(settings_file.read_text())
        assert first == restored

    def test_uninstall_empty_hooks_drops_key(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"hooks": {}}))
        ClaudePlatform(settings_file=settings_file).uninstall()
        settings = json.loads(settings_file.read_text())
        assert "hooks" not in settings


class TestDefaultSettingsFile:
    def test_default_settings_file_matches_constants(self):
        from atrace.platforms.claude.constants import SETTINGS_FILE

        p = ClaudePlatform()
        assert p._settings_file == SETTINGS_FILE


class TestHookEntryStructure:
    def test_hook_structure_matches_claude_schema(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        ClaudePlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        for event, entries in settings["hooks"].items():
            assert isinstance(entries, list)
            for entry in entries:
                assert "hooks" in entry
                assert isinstance(entry["hooks"], list)
                for h in entry["hooks"]:
                    assert set(h.keys()) == {"type", "command"}
                    assert h["type"] == "command"

    def test_all_ten_events_registered(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        ClaudePlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        assert len(settings["hooks"]) == 10
