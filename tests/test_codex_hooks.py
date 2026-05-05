from __future__ import annotations

import json
from pathlib import Path

import pytest

from thirdeye.config import Config
from thirdeye.store import Store


@pytest.fixture
def env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("THIRDEYE_HOME", str(tmp_path))
    return tmp_path


def _argv(monkeypatch, payload: dict) -> None:
    monkeypatch.setattr("sys.argv", ["notify", json.dumps(payload)])


# -- _read_argv ----------------------------------------------------------------


class TestReadArgv:
    def test_valid_json_returns_dict(self, monkeypatch):
        from thirdeye.platforms.codex import hooks

        _argv(monkeypatch, {"thread-id": "abc", "cwd": "/p"})
        result = hooks._read_argv()
        assert result == {"thread-id": "abc", "cwd": "/p"}

    def test_missing_argv_returns_empty_dict(self, monkeypatch):
        from thirdeye.platforms.codex import hooks

        monkeypatch.setattr("sys.argv", ["notify"])
        assert hooks._read_argv() == {}

    def test_invalid_json_returns_empty_dict(self, monkeypatch):
        from thirdeye.platforms.codex import hooks

        monkeypatch.setattr("sys.argv", ["notify", "not json"])
        assert hooks._read_argv() == {}

    def test_empty_string_argv_returns_empty_dict(self, monkeypatch):
        from thirdeye.platforms.codex import hooks

        monkeypatch.setattr("sys.argv", ["notify", ""])
        assert hooks._read_argv() == {}


# -- _strip_payload ------------------------------------------------------------


class TestStripPayload:
    def test_strips_thread_id_kebab(self):
        from thirdeye.platforms.codex import hooks

        result = hooks._strip_payload({"thread-id": "abc", "extra": 1})
        assert "thread-id" not in result

    def test_strips_thread_id_snake(self):
        from thirdeye.platforms.codex import hooks

        result = hooks._strip_payload({"thread_id": "abc", "extra": 1})
        assert "thread_id" not in result

    def test_strips_threadId_camel(self):
        from thirdeye.platforms.codex import hooks

        result = hooks._strip_payload({"threadId": "abc", "extra": 1})
        assert "threadId" not in result

    def test_strips_cwd(self):
        from thirdeye.platforms.codex import hooks

        result = hooks._strip_payload({"cwd": "/p", "extra": 1})
        assert "cwd" not in result

    def test_strips_working_directory_kebab(self):
        from thirdeye.platforms.codex import hooks

        result = hooks._strip_payload({"working-directory": "/p", "extra": 1})
        assert "working-directory" not in result

    def test_strips_working_directory_snake(self):
        from thirdeye.platforms.codex import hooks

        result = hooks._strip_payload({"working_directory": "/p", "extra": 1})
        assert "working_directory" not in result

    def test_preserves_other_keys(self):
        from thirdeye.platforms.codex import hooks

        payload = {
            "thread-id": "abc",
            "cwd": "/p",
            "type": "agent-turn-complete",
            "token_usage": {"input": 100},
        }
        result = hooks._strip_payload(payload)
        assert result == {"type": "agent-turn-complete", "token_usage": {"input": 100}}


# -- _emit ---------------------------------------------------------------------


class TestEmit:
    def test_routes_thread_id_kebab_as_session_id(self, monkeypatch, env: Path):
        from thirdeye.platforms.codex import hooks

        result = hooks._emit("agent_turn", {"thread-id": "abc-123", "cwd": "/p"})
        assert result is True
        metas = list(Store(Config.load()).list_sessions())
        assert len(metas) == 1
        assert metas[0].session_id == "abc-123"

    def test_routes_thread_id_snake_as_session_id(self, monkeypatch, env: Path):
        from thirdeye.platforms.codex import hooks

        result = hooks._emit("agent_turn", {"thread_id": "snake-123", "cwd": "/p"})
        assert result is True
        metas = list(Store(Config.load()).list_sessions())
        assert len(metas) == 1
        assert metas[0].session_id == "snake-123"

    def test_routes_threadId_camel_as_session_id(self, monkeypatch, env: Path):
        from thirdeye.platforms.codex import hooks

        result = hooks._emit("agent_turn", {"threadId": "camel-123", "cwd": "/p"})
        assert result is True
        metas = list(Store(Config.load()).list_sessions())
        assert len(metas) == 1
        assert metas[0].session_id == "camel-123"

    def test_uses_cwd_from_payload(self, monkeypatch, env: Path):
        from thirdeye.platforms.codex import hooks

        hooks._emit("agent_turn", {"thread-id": "s1", "cwd": "/my/project"})
        m = next(Store(Config.load()).list_sessions())
        assert m.cwd == "/my/project"

    def test_uses_working_directory_if_cwd_absent(self, monkeypatch, env: Path):
        from thirdeye.platforms.codex import hooks

        hooks._emit("agent_turn", {"thread-id": "s1", "working-directory": "/alt/path"})
        m = next(Store(Config.load()).list_sessions())
        assert m.cwd == "/alt/path"

    def test_falls_back_to_os_getcwd(self, monkeypatch, env: Path):
        from thirdeye.platforms.codex import hooks

        monkeypatch.chdir(env)
        hooks._emit("agent_turn", {"thread-id": "s1"})
        m = next(Store(Config.load()).list_sessions())
        assert m.cwd == str(env)

    def test_returns_false_when_no_thread_id(self, monkeypatch, env: Path):
        from thirdeye.platforms.codex import hooks

        result = hooks._emit("agent_turn", {"cwd": "/p"})
        assert result is False
        assert list(Store(Config.load()).list_sessions()) == []

    def test_stores_platform_as_codex(self, monkeypatch, env: Path):
        from thirdeye.platforms.codex import hooks

        hooks._emit("agent_turn", {"thread-id": "s1", "cwd": "/p"})
        m = next(Store(Config.load()).list_sessions())
        assert m.platform == "codex"

    def test_strips_routing_keys_from_data(self, monkeypatch, env: Path):
        from thirdeye.platforms.codex import hooks

        hooks._emit("agent_turn", {"thread-id": "s1", "cwd": "/p", "extra": 42})
        events = list(Store(Config.load()).reader("s1").iter_events())
        data = events[0].get("data", {})
        assert "thread-id" not in data
        assert "cwd" not in data
        assert data["extra"] == 42


# -- notify --------------------------------------------------------------------


class TestNotify:
    def test_agent_turn_complete_creates_event(self, monkeypatch, env: Path):
        from thirdeye.platforms.codex import hooks

        payload = {
            "type": "agent-turn-complete",
            "thread-id": "t-001",
            "cwd": "/project",
            "token_usage": {"input": 100, "output": 50},
        }
        _argv(monkeypatch, payload)
        hooks.notify()
        store = Store(Config.load())
        metas = list(store.list_sessions())
        assert len(metas) == 1
        assert metas[0].session_id == "t-001"
        assert metas[0].platform == "codex"
        events = list(store.reader("t-001").iter_events())
        assert len(events) == 1
        assert events[0]["t"] == "agent_turn"
        data = events[0]["data"]
        assert "thread-id" not in data
        assert "cwd" not in data
        assert data["token_usage"] == {"input": 100, "output": 50}

    def test_wrong_type_is_silent_noop(self, monkeypatch, env: Path):
        from thirdeye.platforms.codex import hooks

        payload = {"type": "something-else", "thread-id": "t-001", "cwd": "/p"}
        _argv(monkeypatch, payload)
        hooks.notify()
        assert list(Store(Config.load()).list_sessions()) == []

    def test_no_payload_is_silent_noop(self, monkeypatch, env: Path):
        from thirdeye.platforms.codex import hooks

        monkeypatch.setattr("sys.argv", ["notify"])
        hooks.notify()
        assert list(Store(Config.load()).list_sessions()) == []

    def test_bad_json_in_argv_is_silent_noop(self, monkeypatch, env: Path):
        from thirdeye.platforms.codex import hooks

        monkeypatch.setattr("sys.argv", ["notify", "not valid json"])
        hooks.notify()
        assert list(Store(Config.load()).list_sessions()) == []

    def test_preserves_nested_fields_in_data(self, monkeypatch, env: Path):
        from thirdeye.platforms.codex import hooks

        payload = {
            "type": "agent-turn-complete",
            "thread-id": "t-002",
            "cwd": "/proj",
            "last-assistant-message": "Here is the answer.",
            "input-messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ],
            "token_usage": {"input": 200, "output": 100, "total": 300},
            "tool_calls": [
                {"name": "Read", "input": {"file": "x.py"}},
                {"name": "Bash", "input": {"command": "ls"}},
            ],
        }
        _argv(monkeypatch, payload)
        hooks.notify()
        events = list(Store(Config.load()).reader("t-002").iter_events())
        data = events[0]["data"]
        assert data["last-assistant-message"] == "Here is the answer."
        assert data["input-messages"] == [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        assert data["token_usage"] == {"input": 200, "output": 100, "total": 300}
        assert data["tool_calls"] == [
            {"name": "Read", "input": {"file": "x.py"}},
            {"name": "Bash", "input": {"command": "ls"}},
        ]

    def test_does_not_print_to_stdout(self, monkeypatch, env: Path, capsys):
        from thirdeye.platforms.codex import hooks

        payload = {
            "type": "agent-turn-complete",
            "thread-id": "t-003",
            "cwd": "/p",
        }
        _argv(monkeypatch, payload)
        hooks.notify()
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_noop_does_not_print_to_stdout(self, monkeypatch, env: Path, capsys):
        from thirdeye.platforms.codex import hooks

        monkeypatch.setattr("sys.argv", ["notify"])
        hooks.notify()
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_missing_thread_id_is_silent_noop(self, monkeypatch, env: Path):
        from thirdeye.platforms.codex import hooks

        payload = {"type": "agent-turn-complete", "cwd": "/p"}
        _argv(monkeypatch, payload)
        hooks.notify()
        assert list(Store(Config.load()).list_sessions()) == []


# -- platform constant ---------------------------------------------------------


class TestPlatformConstant:
    def test_platform_is_codex(self):
        from thirdeye.platforms.codex import hooks

        assert hooks._PLATFORM == "codex"


# -- _flex_get -----------------------------------------------------------------


class TestFlexGet:
    def test_returns_first_matching_key(self):
        from thirdeye.platforms.codex import hooks

        d = {"thread-id": "abc"}
        assert hooks._flex_get(d, "thread-id", "thread_id", "threadId") == "abc"

    def test_returns_second_key_if_first_missing(self):
        from thirdeye.platforms.codex import hooks

        d = {"thread_id": "def"}
        assert hooks._flex_get(d, "thread-id", "thread_id", "threadId") == "def"

    def test_returns_third_key_if_others_missing(self):
        from thirdeye.platforms.codex import hooks

        d = {"threadId": "ghi"}
        assert hooks._flex_get(d, "thread-id", "thread_id", "threadId") == "ghi"

    def test_returns_default_when_no_keys_match(self):
        from thirdeye.platforms.codex import hooks

        d = {"other": "val"}
        assert hooks._flex_get(d, "thread-id", "thread_id", "threadId") is None

    def test_returns_custom_default(self):
        from thirdeye.platforms.codex import hooks

        d = {"other": "val"}
        assert hooks._flex_get(d, "thread-id", default="fallback") == "fallback"

    def test_skips_empty_string_values(self):
        from thirdeye.platforms.codex import hooks

        d = {"thread-id": "", "thread_id": "notempty"}
        assert hooks._flex_get(d, "thread-id", "thread_id") == "notempty"

    def test_skips_none_values(self):
        from thirdeye.platforms.codex import hooks

        d = {"thread-id": None, "threadId": "found"}
        assert hooks._flex_get(d, "thread-id", "threadId") == "found"
