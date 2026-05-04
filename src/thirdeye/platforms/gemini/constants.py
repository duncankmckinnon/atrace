from __future__ import annotations

from pathlib import Path

PLATFORM_NAME = "gemini"
DISPLAY_NAME = "Gemini CLI"
SETTINGS_DIR = Path.home() / ".gemini"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

# Friendly hook name written into settings.json — used by uninstall to identify
# entries to remove.
HOOK_NAME = "thirdeye-tracing"

# Per-hook timeout in milliseconds (Gemini's own default is 60000; we use 30s
# so a wedged hook can't stall the user's CLI for too long).
HOOK_TIMEOUT_MS = 30000

# Map of Gemini hook event name -> CLI entry-point script name registered
# in pyproject.toml [project.scripts]. Order is preserved when writing
# settings.json.
HOOK_EVENTS: dict[str, str] = {
    "SessionStart": "thirdeye-gemini-session-start",
    "SessionEnd": "thirdeye-gemini-session-end",
    "BeforeAgent": "thirdeye-gemini-before-agent",
    "AfterAgent": "thirdeye-gemini-after-agent",
    "BeforeModel": "thirdeye-gemini-before-model",
    "AfterModel": "thirdeye-gemini-after-model",
    "BeforeTool": "thirdeye-gemini-before-tool",
    "AfterTool": "thirdeye-gemini-after-tool",
}
