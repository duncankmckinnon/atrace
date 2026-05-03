from __future__ import annotations

import json
import shutil
from pathlib import Path

from thirdeye.platforms.base import Platform
from thirdeye.platforms.claude.constants import (
    DISPLAY_NAME,
    HOOK_EVENTS,
    PLATFORM_NAME,
    SETTINGS_FILE,
)


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def _resolve_command(script_name: str) -> str:
    return shutil.which(script_name) or script_name


class ClaudePlatform(Platform):
    name = PLATFORM_NAME
    display_name = DISPLAY_NAME

    def __init__(self, settings_file: Path | None = None) -> None:
        self._settings_file = settings_file or SETTINGS_FILE

    def install(self) -> None:
        settings = _load(self._settings_file)
        hooks = settings.setdefault("hooks", {})
        for event, script in HOOK_EVENTS.items():
            cmd = _resolve_command(script)
            entries = hooks.setdefault(event, [])
            already = any(
                h.get("command") == cmd for entry in entries for h in entry.get("hooks", [])
            )
            if not already:
                entries.append({"hooks": [{"type": "command", "command": cmd}]})
        _save(self._settings_file, settings)

    def uninstall(self) -> None:
        if not self._settings_file.exists():
            return
        settings = _load(self._settings_file)
        if "hooks" not in settings:
            return
        our_scripts = set(HOOK_EVENTS.values())
        hooks = settings["hooks"]
        for event in list(hooks.keys()):
            entries = hooks[event]
            filtered = [
                entry
                for entry in entries
                if not all(
                    Path(h.get("command", "")).name in our_scripts for h in entry.get("hooks", [])
                )
            ]
            if filtered:
                hooks[event] = filtered
            else:
                del hooks[event]
        if not hooks:
            del settings["hooks"]
        _save(self._settings_file, settings)
