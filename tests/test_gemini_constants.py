from __future__ import annotations

from thirdeye.platforms.gemini.constants import (
    DISPLAY_NAME,
    HOOK_EVENTS,
    HOOK_NAME,
    HOOK_TIMEOUT_MS,
    PLATFORM_NAME,
    SETTINGS_DIR,
    SETTINGS_FILE,
)


def test_platform_name():
    assert PLATFORM_NAME == "gemini"


def test_display_name():
    assert DISPLAY_NAME == "Gemini CLI"


def test_settings_file_under_gemini_home():
    parts = SETTINGS_FILE.parts
    assert ".gemini" in parts
    assert parts[-1] == "settings.json"


def test_settings_dir_is_parent_of_settings_file():
    assert SETTINGS_FILE.parent == SETTINGS_DIR


def test_hook_events_has_exactly_eight_entries():
    assert len(HOOK_EVENTS) == 8


def test_hook_events_covers_known_lifecycle():
    expected = {
        "SessionStart",
        "SessionEnd",
        "BeforeAgent",
        "AfterAgent",
        "BeforeModel",
        "AfterModel",
        "BeforeTool",
        "AfterTool",
    }
    assert set(HOOK_EVENTS.keys()) == expected


def test_hook_event_scripts_unique():
    assert len(set(HOOK_EVENTS.values())) == len(HOOK_EVENTS)


def test_hook_event_scripts_have_thirdeye_gemini_prefix():
    for script in HOOK_EVENTS.values():
        assert script.startswith("thirdeye-gemini-")


def test_hook_timeout_ms():
    assert HOOK_TIMEOUT_MS == 30000


def test_hook_name():
    assert HOOK_NAME == "thirdeye-tracing"
