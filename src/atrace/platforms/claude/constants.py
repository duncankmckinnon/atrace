from __future__ import annotations

from pathlib import Path

PLATFORM_NAME = "claude"
DISPLAY_NAME = "Claude Code"
SETTINGS_FILE = Path.home() / ".claude" / "settings.json"

HOOK_EVENTS: dict[str, str] = {
    "SessionStart": "atrace-claude-session-start",
    "UserPromptSubmit": "atrace-claude-user-prompt-submit",
    "PreToolUse": "atrace-claude-pre-tool-use",
    "PostToolUse": "atrace-claude-post-tool-use",
    "Stop": "atrace-claude-stop",
    "SubagentStop": "atrace-claude-subagent-stop",
    "StopFailure": "atrace-claude-stop-failure",
    "Notification": "atrace-claude-notification",
    "PermissionRequest": "atrace-claude-permission-request",
    "SessionEnd": "atrace-claude-session-end",
}
