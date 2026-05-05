from __future__ import annotations

import json
from pathlib import Path

from thirdeye.platforms.gemini.constants import (
    HOOK_EVENTS,
    HOOK_NAME,
    HOOK_TIMEOUT_MS,
    SETTINGS_FILE,
)
from thirdeye.platforms.gemini.install import GeminiPlatform


class TestGeminiPlatformAttributes:
    def test_name_is_gemini(self):
        p = GeminiPlatform(settings_file=Path("/fake/settings.json"))
        assert p.name == "gemini"

    def test_display_name(self):
        p = GeminiPlatform(settings_file=Path("/fake/settings.json"))
        assert p.display_name == "Gemini CLI"

    def test_is_platform_subclass(self):
        from thirdeye.platforms.base import Platform

        assert issubclass(GeminiPlatform, Platform)

    def test_default_settings_file_matches_constants(self):
        p = GeminiPlatform()
        assert p._settings_file == SETTINGS_FILE


class TestInstallFreshFile:
    def test_writes_all_eight_hook_events(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        assert set(settings["hooks"].keys()) == set(HOOK_EVENTS.keys())

    def test_creates_parent_dir(self, tmp_path: Path):
        settings_file = tmp_path / "nested" / "deeper" / "settings.json"
        GeminiPlatform(settings_file=settings_file).install()
        assert settings_file.exists()

    def test_each_event_has_one_block(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        for event, blocks in settings["hooks"].items():
            assert len(blocks) == 1, f"expected 1 block for {event}"

    def test_block_has_matcher_field(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        for event, blocks in settings["hooks"].items():
            for block in blocks:
                assert "matcher" in block, f"missing matcher in block for {event}"
                assert block["matcher"] == ""

    def test_hook_has_name_field(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        for blocks in settings["hooks"].values():
            for block in blocks:
                for h in block["hooks"]:
                    assert h["name"] == HOOK_NAME

    def test_hook_has_type_command(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        for blocks in settings["hooks"].values():
            for block in blocks:
                for h in block["hooks"]:
                    assert h["type"] == "command"

    def test_hook_has_command_string(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        for blocks in settings["hooks"].values():
            for block in blocks:
                for h in block["hooks"]:
                    assert "command" in h
                    assert isinstance(h["command"], str)

    def test_hook_has_timeout(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        for blocks in settings["hooks"].values():
            for block in blocks:
                for h in block["hooks"]:
                    assert h["timeout"] == HOOK_TIMEOUT_MS

    def test_command_contains_script_name(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        for event, script in HOOK_EVENTS.items():
            cmds = [h["command"] for block in settings["hooks"][event] for h in block["hooks"]]
            assert any(script in c for c in cmds), f"{script} not in commands for {event}"

    def test_hook_block_structure(self, tmp_path: Path):
        """Each block has matcher + hooks list; each hook has type, name, command, timeout."""
        settings_file = tmp_path / "settings.json"
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        for event, blocks in settings["hooks"].items():
            assert isinstance(blocks, list)
            for block in blocks:
                assert set(block.keys()) == {"matcher", "hooks"}
                assert isinstance(block["hooks"], list)
                for h in block["hooks"]:
                    assert set(h.keys()) == {"type", "name", "command", "timeout"}

    def test_output_is_valid_json(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        GeminiPlatform(settings_file=settings_file).install()
        json.loads(settings_file.read_text())

    def test_file_ends_with_newline(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        GeminiPlatform(settings_file=settings_file).install()
        assert settings_file.read_text().endswith("\n")

    def test_exactly_eight_events_registered(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        assert len(settings["hooks"]) == 8


class TestInstallIdempotent:
    def test_no_duplicate_blocks(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        p = GeminiPlatform(settings_file=settings_file)
        p.install()
        p.install()
        settings = json.loads(settings_file.read_text())
        for event, blocks in settings["hooks"].items():
            assert len(blocks) == 1, f"expected 1 block for {event} after 2 installs"

    def test_no_duplicate_blocks_triple_install(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        p = GeminiPlatform(settings_file=settings_file)
        p.install()
        p.install()
        p.install()
        settings = json.loads(settings_file.read_text())
        for event, blocks in settings["hooks"].items():
            assert len(blocks) == 1, f"expected 1 block for {event} after 3 installs"

    def test_content_identical_after_double_install(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        p = GeminiPlatform(settings_file=settings_file)
        p.install()
        first = settings_file.read_text()
        p.install()
        second = settings_file.read_text()
        assert first == second


class TestInstallPreservesExisting:
    def test_preserves_unrelated_top_level_keys(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"security": {"sandboxing": True}, "theme": "dark"}))
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        assert settings["security"] == {"sandboxing": True}
        assert settings["theme"] == "dark"
        assert "hooks" in settings

    def test_preserves_other_tools_hook_blocks(self, tmp_path: Path):
        """Blocks where no inner hook has name == HOOK_NAME should be kept."""
        settings_file = tmp_path / "settings.json"
        foreign_block = {
            "matcher": "",
            "hooks": [
                {
                    "type": "command",
                    "name": "other-tracing-tool",
                    "command": "/usr/bin/other-tool",
                    "timeout": 60000,
                }
            ],
        }
        settings_file.write_text(json.dumps({"hooks": {"SessionStart": [foreign_block]}}))
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        blocks = settings["hooks"]["SessionStart"]
        # Should have the foreign block + our block
        assert len(blocks) == 2
        names = [h["name"] for block in blocks for h in block["hooks"]]
        assert "other-tracing-tool" in names
        assert HOOK_NAME in names

    def test_preserves_hooks_for_unknown_events(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(
            json.dumps(
                {
                    "hooks": {
                        "CustomEvent": [
                            {
                                "matcher": "",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "name": "custom-hook",
                                        "command": "/custom/hook",
                                        "timeout": 10000,
                                    }
                                ],
                            }
                        ]
                    }
                }
            )
        )
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        assert "CustomEvent" in settings["hooks"]
        cmds = [h["command"] for block in settings["hooks"]["CustomEvent"] for h in block["hooks"]]
        assert "/custom/hook" in cmds


class TestInstallEdgeCases:
    def test_handles_empty_file(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text("")
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        assert set(settings["hooks"].keys()) == set(HOOK_EVENTS.keys())

    def test_handles_malformed_json(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text("{invalid json")
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        assert set(settings["hooks"].keys()) == set(HOOK_EVENTS.keys())

    def test_handles_empty_hooks_dict(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"hooks": {}}))
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        assert set(settings["hooks"].keys()) == set(HOOK_EVENTS.keys())

    def test_handles_empty_event_list(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"hooks": {"SessionStart": []}}))
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        assert len(settings["hooks"]["SessionStart"]) == 1

    def test_existing_block_from_us_is_replaced_not_duplicated(self, tmp_path: Path):
        """If a block already has our HOOK_NAME, reinstall should replace it."""
        settings_file = tmp_path / "settings.json"
        old_block = {
            "matcher": "",
            "hooks": [
                {
                    "type": "command",
                    "name": HOOK_NAME,
                    "command": "/old/path/thirdeye-gemini-session-start",
                    "timeout": 10000,
                }
            ],
        }
        settings_file.write_text(json.dumps({"hooks": {"SessionStart": [old_block]}}))
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        blocks = settings["hooks"]["SessionStart"]
        our_blocks = [
            block for block in blocks if any(h.get("name") == HOOK_NAME for h in block["hooks"])
        ]
        assert len(our_blocks) == 1, "should have exactly one block with our hook name"
        # The timeout should be updated to the current constant
        assert our_blocks[0]["hooks"][0]["timeout"] == HOOK_TIMEOUT_MS

    def test_nonexistent_file_treated_as_empty(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        assert not settings_file.exists()
        GeminiPlatform(settings_file=settings_file).install()
        assert settings_file.exists()
        settings = json.loads(settings_file.read_text())
        assert set(settings["hooks"].keys()) == set(HOOK_EVENTS.keys())


class TestUninstallRemovesHooks:
    def test_removes_all_our_hooks(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"theme": "dark"}))
        p = GeminiPlatform(settings_file=settings_file)
        p.install()
        p.uninstall()
        # After uninstall with only our hooks, hooks key should be gone
        settings = json.loads(settings_file.read_text())
        assert "hooks" not in settings

    def test_drops_empty_event_keys(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"theme": "dark"}))
        p = GeminiPlatform(settings_file=settings_file)
        p.install()
        p.uninstall()
        settings = json.loads(settings_file.read_text())
        for event in HOOK_EVENTS:
            assert event not in settings.get("hooks", {})

    def test_drops_empty_hooks_key(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"theme": "dark"}))
        p = GeminiPlatform(settings_file=settings_file)
        p.install()
        p.uninstall()
        settings = json.loads(settings_file.read_text())
        assert "hooks" not in settings

    def test_deletes_file_when_settings_becomes_empty(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        p = GeminiPlatform(settings_file=settings_file)
        p.install()
        p.uninstall()
        assert not settings_file.exists()

    def test_preserves_other_settings_on_uninstall(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"security": {"sandboxing": True}}))
        p = GeminiPlatform(settings_file=settings_file)
        p.install()
        p.uninstall()
        settings = json.loads(settings_file.read_text())
        assert settings["security"] == {"sandboxing": True}
        assert "hooks" not in settings

    def test_no_settings_file_is_noop(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        GeminiPlatform(settings_file=settings_file).uninstall()
        assert not settings_file.exists()

    def test_uninstall_idempotent(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        p = GeminiPlatform(settings_file=settings_file)
        p.install()
        p.uninstall()
        p.uninstall()  # second uninstall should not error
        assert not settings_file.exists()

    def test_uninstall_idempotent_with_other_settings(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(json.dumps({"theme": "dark"}))
        p = GeminiPlatform(settings_file=settings_file)
        p.install()
        p.uninstall()
        first = settings_file.read_text()
        p.uninstall()
        second = settings_file.read_text()
        assert first == second

    def test_uninstall_then_install_restores(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        p = GeminiPlatform(settings_file=settings_file)
        p.install()
        first = json.loads(settings_file.read_text())
        p.uninstall()
        p.install()
        restored = json.loads(settings_file.read_text())
        assert first == restored


class TestUninstallPreservesForeign:
    def test_leaves_other_tools_blocks_intact(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        foreign_block = {
            "matcher": "",
            "hooks": [
                {
                    "type": "command",
                    "name": "other-tracing-tool",
                    "command": "/usr/bin/other-tool",
                    "timeout": 60000,
                }
            ],
        }
        settings_file.write_text(json.dumps({"hooks": {"SessionStart": [foreign_block]}}))
        p = GeminiPlatform(settings_file=settings_file)
        p.install()
        p.uninstall()
        settings = json.loads(settings_file.read_text())
        assert "SessionStart" in settings["hooks"]
        names = [h["name"] for block in settings["hooks"]["SessionStart"] for h in block["hooks"]]
        assert "other-tracing-tool" in names
        assert HOOK_NAME not in names

    def test_foreign_blocks_on_multiple_events(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        foreign = {
            "matcher": "",
            "hooks": [
                {
                    "type": "command",
                    "name": "foreign-hook",
                    "command": "/usr/bin/foreign",
                    "timeout": 10000,
                }
            ],
        }
        settings_file.write_text(
            json.dumps(
                {
                    "hooks": {
                        "SessionStart": [foreign],
                        "BeforeModel": [foreign],
                    }
                }
            )
        )
        p = GeminiPlatform(settings_file=settings_file)
        p.install()
        p.uninstall()
        settings = json.loads(settings_file.read_text())
        assert "SessionStart" in settings["hooks"]
        assert "BeforeModel" in settings["hooks"]
        # Our events that had no foreign blocks should be gone
        for event in HOOK_EVENTS:
            if event not in ("SessionStart", "BeforeModel"):
                assert event not in settings["hooks"]

    def test_uninstall_with_no_thirdeye_hooks_present(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        settings_file.write_text(
            json.dumps(
                {
                    "hooks": {
                        "SessionStart": [
                            {
                                "matcher": "",
                                "hooks": [
                                    {
                                        "type": "command",
                                        "name": "other-tool",
                                        "command": "/other/tool",
                                        "timeout": 5000,
                                    }
                                ],
                            }
                        ]
                    }
                }
            )
        )
        GeminiPlatform(settings_file=settings_file).uninstall()
        settings = json.loads(settings_file.read_text())
        assert "/other/tool" in [
            h["command"] for block in settings["hooks"]["SessionStart"] for h in block["hooks"]
        ]


class TestResolveCommandAbsolutePath:
    def test_install_uses_absolute_path_when_which_resolves(self, tmp_path: Path, monkeypatch):
        settings_file = tmp_path / "settings.json"

        def fake_which(name):
            return f"/usr/local/bin/{name}"

        monkeypatch.setattr("thirdeye.platforms.gemini.install.shutil.which", fake_which)
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        for event, script in HOOK_EVENTS.items():
            cmds = [h["command"] for block in settings["hooks"][event] for h in block["hooks"]]
            assert cmds == [f"/usr/local/bin/{script}"]

    def test_install_falls_back_to_bare_name_when_which_fails(self, tmp_path: Path, monkeypatch):
        settings_file = tmp_path / "settings.json"
        monkeypatch.setattr("thirdeye.platforms.gemini.install.shutil.which", lambda _: None)
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        for event, script in HOOK_EVENTS.items():
            cmds = [h["command"] for block in settings["hooks"][event] for h in block["hooks"]]
            assert cmds == [script]

    def test_uninstall_removes_absolute_path_hooks(self, tmp_path: Path, monkeypatch):
        settings_file = tmp_path / "settings.json"

        def fake_which(name):
            return f"/usr/local/bin/{name}"

        monkeypatch.setattr("thirdeye.platforms.gemini.install.shutil.which", fake_which)
        p = GeminiPlatform(settings_file=settings_file)
        p.install()
        p.uninstall()
        assert not settings_file.exists()

    def test_idempotent_with_absolute_paths(self, tmp_path: Path, monkeypatch):
        settings_file = tmp_path / "settings.json"

        def fake_which(name):
            return f"/opt/bin/{name}"

        monkeypatch.setattr("thirdeye.platforms.gemini.install.shutil.which", fake_which)
        p = GeminiPlatform(settings_file=settings_file)
        p.install()
        first = settings_file.read_text()
        p.install()
        second = settings_file.read_text()
        assert first == second
