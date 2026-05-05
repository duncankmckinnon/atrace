from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from thirdeye.config import Config
from thirdeye.platforms.gemini import hooks as g_hooks
from thirdeye.platforms.gemini.install import GeminiPlatform
from thirdeye.store import Store


@pytest.fixture
def env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("THIRDEYE_HOME", str(tmp_path))
    return tmp_path


def _stdin(monkeypatch, payload: dict) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))


# -- install -------------------------------------------------------------------


class TestGeminiInstall:
    def test_install_writes_settings_file(self, tmp_path: Path):
        settings_file = tmp_path / ".gemini" / "settings.json"
        GeminiPlatform(settings_file=settings_file).install()
        assert settings_file.exists()

    def test_install_writes_all_eight_events(self, tmp_path: Path):
        settings_file = tmp_path / ".gemini" / "settings.json"
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        expected_events = {
            "SessionStart",
            "SessionEnd",
            "BeforeAgent",
            "AfterAgent",
            "BeforeModel",
            "AfterModel",
            "BeforeTool",
            "AfterTool",
        }
        assert set(settings["hooks"].keys()) == expected_events

    def test_install_each_hook_has_command_type(self, tmp_path: Path):
        settings_file = tmp_path / ".gemini" / "settings.json"
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        for event, blocks in settings["hooks"].items():
            for block in blocks:
                for h in block["hooks"]:
                    assert h["type"] == "command", f"{event} hook type != command"
                    assert "command" in h

    def test_install_each_hook_has_thirdeye_gemini_command(self, tmp_path: Path):
        settings_file = tmp_path / ".gemini" / "settings.json"
        GeminiPlatform(settings_file=settings_file).install()
        settings = json.loads(settings_file.read_text())
        for event, blocks in settings["hooks"].items():
            cmds = [h["command"] for block in blocks for h in block["hooks"]]
            assert any(
                "thirdeye-gemini" in c for c in cmds
            ), f"no thirdeye-gemini command for {event}"

    def test_install_idempotent(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        p = GeminiPlatform(settings_file=settings_file)
        p.install()
        first = settings_file.read_text()
        p.install()
        second = settings_file.read_text()
        assert first == second

    def test_install_output_is_valid_json(self, tmp_path: Path):
        settings_file = tmp_path / "settings.json"
        GeminiPlatform(settings_file=settings_file).install()
        json.loads(settings_file.read_text())  # should not raise


# -- full lifecycle ------------------------------------------------------------


class TestGeminiFullLifecycle:
    def test_full_session_lifecycle(self, monkeypatch, env: Path):
        """Drive all 8 hooks in order and verify events are stored correctly."""
        sid = "gemini-e2e-001"
        base = {"session_id": sid, "cwd": "/proj/gemini"}

        # SessionStart
        _stdin(monkeypatch, {**base, "source": "cli"})
        g_hooks.session_start()

        # BeforeAgent
        _stdin(monkeypatch, {**base, "input": "explain this"})
        g_hooks.before_agent()

        # BeforeModel
        _stdin(monkeypatch, {**base, "model": "gemini-pro"})
        g_hooks.before_model()

        # AfterModel
        _stdin(monkeypatch, {**base, "response": "Here is the explanation"})
        g_hooks.after_model()

        # BeforeTool
        _stdin(monkeypatch, {**base, "tool_name": "search", "query": "test"})
        g_hooks.before_tool()

        # AfterTool
        _stdin(monkeypatch, {**base, "tool_name": "search", "result": "found it"})
        g_hooks.after_tool()

        # AfterAgent
        _stdin(monkeypatch, {**base, "output": "done"})
        g_hooks.after_agent()

        # SessionEnd
        _stdin(monkeypatch, base)
        g_hooks.session_end()

        store = Store(Config.load())
        events = list(store.reader(sid).iter_events())
        types = [e["t"] for e in events]
        assert types == [
            "session_start",
            "user_message",
            "model_request",
            "model_response",
            "tool_call",
            "tool_result",
            "assistant_message",
            "session_end",
        ]

    def test_session_end_closes_session(self, monkeypatch, env: Path):
        sid = "gemini-close-001"
        base = {"session_id": sid, "cwd": "/proj/x"}

        _stdin(monkeypatch, base)
        g_hooks.session_start()
        _stdin(monkeypatch, base)
        g_hooks.session_end()

        store = Store(Config.load())
        m = next(store.list_sessions())
        assert m.status == "closed"
        assert m.ended_at is not None

    def test_platform_is_gemini(self, monkeypatch, env: Path):
        sid = "gemini-plat-001"
        _stdin(monkeypatch, {"session_id": sid, "cwd": "/p"})
        g_hooks.session_start()

        m = next(Store(Config.load()).list_sessions())
        assert m.platform == "gemini"

    def test_event_count_matches(self, monkeypatch, env: Path):
        sid = "gemini-count-001"
        base = {"session_id": sid, "cwd": "/p"}

        _stdin(monkeypatch, base)
        g_hooks.session_start()
        _stdin(monkeypatch, {**base, "input": "hello"})
        g_hooks.before_agent()
        _stdin(monkeypatch, base)
        g_hooks.session_end()

        m = next(Store(Config.load()).list_sessions())
        assert m.event_count == 3


# -- hooks print {} to stdout -------------------------------------------------


class TestGeminiHooksPrintEmptyJson:
    def test_session_start_prints_empty_json(self, monkeypatch, env: Path, capsys):
        _stdin(monkeypatch, {"session_id": "s1", "cwd": "/p"})
        g_hooks.session_start()
        captured = capsys.readouterr()
        assert captured.out.strip() == "{}"

    def test_session_end_prints_empty_json(self, monkeypatch, env: Path, capsys):
        _stdin(monkeypatch, {"session_id": "s1", "cwd": "/p"})
        g_hooks.session_start()
        _stdin(monkeypatch, {"session_id": "s1", "cwd": "/p"})
        g_hooks.session_end()
        captured = capsys.readouterr()
        # Both session_start and session_end print {}
        lines = [line for line in captured.out.strip().splitlines() if line.strip()]
        assert all(line.strip() == "{}" for line in lines)

    def test_before_agent_prints_empty_json(self, monkeypatch, env: Path, capsys):
        _stdin(monkeypatch, {"session_id": "s1", "cwd": "/p"})
        g_hooks.before_agent()
        captured = capsys.readouterr()
        assert captured.out.strip() == "{}"

    def test_after_agent_prints_empty_json(self, monkeypatch, env: Path, capsys):
        _stdin(monkeypatch, {"session_id": "s1", "cwd": "/p"})
        g_hooks.after_agent()
        captured = capsys.readouterr()
        assert captured.out.strip() == "{}"

    def test_before_model_prints_empty_json(self, monkeypatch, env: Path, capsys):
        _stdin(monkeypatch, {"session_id": "s1", "cwd": "/p"})
        g_hooks.before_model()
        captured = capsys.readouterr()
        assert captured.out.strip() == "{}"

    def test_after_model_prints_empty_json(self, monkeypatch, env: Path, capsys):
        _stdin(monkeypatch, {"session_id": "s1", "cwd": "/p"})
        g_hooks.after_model()
        captured = capsys.readouterr()
        assert captured.out.strip() == "{}"

    def test_before_tool_prints_empty_json(self, monkeypatch, env: Path, capsys):
        _stdin(monkeypatch, {"session_id": "s1", "cwd": "/p"})
        g_hooks.before_tool()
        captured = capsys.readouterr()
        assert captured.out.strip() == "{}"

    def test_after_tool_prints_empty_json(self, monkeypatch, env: Path, capsys):
        _stdin(monkeypatch, {"session_id": "s1", "cwd": "/p"})
        g_hooks.after_tool()
        captured = capsys.readouterr()
        assert captured.out.strip() == "{}"

    def test_noop_hook_still_prints_empty_json(self, monkeypatch, env: Path, capsys):
        """Even when session_id is missing, Gemini hooks must print {}."""
        _stdin(monkeypatch, {"cwd": "/p"})
        g_hooks.session_start()
        captured = capsys.readouterr()
        assert captured.out.strip() == "{}"


# -- flexible key lookup -------------------------------------------------------


class TestGeminiFlexibleKeys:
    def test_camel_case_session_id(self, monkeypatch, env: Path):
        _stdin(monkeypatch, {"sessionId": "camel-001", "cwd": "/p"})
        g_hooks.session_start()
        events = list(Store(Config.load()).reader("camel-001").iter_events())
        assert len(events) == 1

    def test_camel_case_working_dir(self, monkeypatch, env: Path):
        _stdin(monkeypatch, {"session_id": "wd-001", "workingDir": "/my/dir"})
        g_hooks.session_start()
        m = next(Store(Config.load()).list_sessions())
        assert m.cwd == "/my/dir"


# -- strip keys ----------------------------------------------------------------


class TestGeminiStripKeys:
    def test_session_id_stripped_from_data(self, monkeypatch, env: Path):
        _stdin(monkeypatch, {"session_id": "s1", "cwd": "/p", "extra": "val"})
        g_hooks.session_start()
        events = list(Store(Config.load()).reader("s1").iter_events())
        data = events[0].get("data", {})
        assert "session_id" not in data
        assert "cwd" not in data
        assert data["extra"] == "val"


# -- silent noop edge cases ----------------------------------------------------


class TestGeminiSilentNoop:
    def test_missing_session_id_is_noop(self, monkeypatch, env: Path):
        _stdin(monkeypatch, {"cwd": "/p"})
        g_hooks.before_agent()
        assert list(Store(Config.load()).list_sessions()) == []

    def test_empty_stdin_is_noop(self, monkeypatch, env: Path):
        monkeypatch.setattr("sys.stdin", io.StringIO(""))
        g_hooks.session_start()
        assert list(Store(Config.load()).list_sessions()) == []

    def test_invalid_json_is_noop(self, monkeypatch, env: Path):
        monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
        g_hooks.before_tool()
        assert list(Store(Config.load()).list_sessions()) == []

    def test_broken_stdin_is_noop(self, monkeypatch, env: Path):
        class BrokenStdin:
            def read(self):
                raise OSError("broken pipe")

        monkeypatch.setattr("sys.stdin", BrokenStdin())
        g_hooks.after_model()
        assert list(Store(Config.load()).list_sessions()) == []
