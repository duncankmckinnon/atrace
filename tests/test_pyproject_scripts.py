"""Tests for pyproject.toml Claude hook console script entries."""

from __future__ import annotations

import importlib
import importlib.metadata
from pathlib import Path

import pytest

from atrace.platforms.claude.constants import HOOK_EVENTS

ROOT = Path(__file__).resolve().parent.parent

EXPECTED_SCRIPTS: dict[str, str] = {
    "atrace-claude-session-start": "atrace.platforms.claude.hooks:session_start",
    "atrace-claude-user-prompt-submit": "atrace.platforms.claude.hooks:user_prompt_submit",
    "atrace-claude-pre-tool-use": "atrace.platforms.claude.hooks:pre_tool_use",
    "atrace-claude-post-tool-use": "atrace.platforms.claude.hooks:post_tool_use",
    "atrace-claude-stop": "atrace.platforms.claude.hooks:stop",
    "atrace-claude-subagent-stop": "atrace.platforms.claude.hooks:subagent_stop",
    "atrace-claude-stop-failure": "atrace.platforms.claude.hooks:stop_failure",
    "atrace-claude-notification": "atrace.platforms.claude.hooks:notification",
    "atrace-claude-permission-request": "atrace.platforms.claude.hooks:permission_request",
    "atrace-claude-session-end": "atrace.platforms.claude.hooks:session_end",
}


class TestPyprojectScriptEntries:
    """Verify pyproject.toml declares all 10 Claude hook scripts."""

    def setup_method(self):
        self.content = (ROOT / "pyproject.toml").read_text()

    @pytest.mark.parametrize("script_name,target", list(EXPECTED_SCRIPTS.items()))
    def test_script_declared_in_pyproject(self, script_name, target):
        expected_line = f'{script_name} = "{target}"'
        assert expected_line in self.content, f"Missing script entry: {expected_line}"

    def test_all_ten_scripts_present(self):
        for script_name, target in EXPECTED_SCRIPTS.items():
            assert f'{script_name} = "{target}"' in self.content

    def test_original_atrace_script_preserved(self):
        assert 'atrace = "atrace.cli:main"' in self.content

    def test_exactly_eleven_scripts(self):
        in_scripts = False
        count = 0
        for line in self.content.splitlines():
            stripped = line.strip()
            if stripped == "[project.scripts]":
                in_scripts = True
                continue
            if in_scripts:
                if stripped.startswith("["):
                    break
                if "=" in stripped and stripped and not stripped.startswith("#"):
                    count += 1
        assert count == 11, f"Expected 11 script entries (1 atrace + 10 hooks), got {count}"


class TestConsoleScriptsRegistered:
    """Verify installed metadata exposes the Claude hook entry points."""

    def _get_atrace_console_scripts(self) -> dict[str, str]:
        eps = importlib.metadata.entry_points(group="console_scripts")
        return {ep.name: ep.value for ep in eps if ep.name.startswith("atrace")}

    @pytest.mark.parametrize("script_name,target", list(EXPECTED_SCRIPTS.items()))
    def test_entrypoint_registered(self, script_name, target):
        scripts = self._get_atrace_console_scripts()
        assert (
            script_name in scripts
        ), f"{script_name} not in registered console_scripts: {sorted(scripts.keys())}"
        assert scripts[script_name] == target

    def test_all_ten_hooks_registered(self):
        scripts = self._get_atrace_console_scripts()
        for name, target in EXPECTED_SCRIPTS.items():
            assert name in scripts
            assert scripts[name] == target

    def test_total_atrace_entrypoints(self):
        scripts = self._get_atrace_console_scripts()
        assert (
            len(scripts) == 11
        ), f"Expected 11 atrace-* console scripts, got {len(scripts)}: {sorted(scripts.keys())}"


class TestScriptNamesMatchConstants:
    """Verify HOOK_EVENTS values in constants.py match pyproject.toml script names."""

    def test_hook_events_values_match_expected_scripts(self):
        assert set(HOOK_EVENTS.values()) == set(EXPECTED_SCRIPTS.keys())

    def test_hook_events_count(self):
        assert len(HOOK_EVENTS) == 10

    @pytest.mark.parametrize("event,script_name", list(HOOK_EVENTS.items()))
    def test_each_hook_event_maps_to_expected_script(self, event, script_name):
        assert (
            script_name in EXPECTED_SCRIPTS
        ), f"HOOK_EVENTS[{event!r}] = {script_name!r} not in expected scripts"


class TestEntryPointFunctionsCallable:
    """Verify each script target resolves to a callable function."""

    @pytest.mark.parametrize("script_name,target", list(EXPECTED_SCRIPTS.items()))
    def test_target_function_importable(self, script_name, target):
        module_path, func_name = target.rsplit(":", 1)
        mod = importlib.import_module(module_path)
        fn = getattr(mod, func_name)
        assert callable(fn), f"{target} is not callable"

    @pytest.mark.parametrize("script_name,target", list(EXPECTED_SCRIPTS.items()))
    def test_target_function_takes_no_args(self, script_name, target):
        import inspect

        module_path, func_name = target.rsplit(":", 1)
        mod = importlib.import_module(module_path)
        fn = getattr(mod, func_name)
        sig = inspect.signature(fn)
        required = [
            p
            for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty
            and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        ]
        assert (
            len(required) == 0
        ), f"{target} requires {len(required)} args, but console scripts call with no args"


class TestScriptBinaryExists:
    """Verify script binaries are installed in the virtualenv."""

    def _venv_bin(self) -> Path:
        venv = ROOT / ".venv"
        bin_dir = venv / "bin"
        if not bin_dir.exists():
            bin_dir = venv / "Scripts"
        return bin_dir

    @pytest.mark.parametrize("script_name", list(EXPECTED_SCRIPTS.keys()))
    def test_script_binary_in_venv(self, script_name):
        bin_dir = self._venv_bin()
        script_path = bin_dir / script_name
        assert script_path.exists(), f"Script binary {script_name} not found in {bin_dir}"

    def test_atrace_binary_still_exists(self):
        bin_dir = self._venv_bin()
        assert (bin_dir / "atrace").exists()
