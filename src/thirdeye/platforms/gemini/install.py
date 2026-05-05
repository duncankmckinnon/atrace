from __future__ import annotations

import json
import shutil
from pathlib import Path

from thirdeye.platforms.base import Platform
from thirdeye.platforms.gemini.constants import (
    DISPLAY_NAME,
    HOOK_EVENTS,
    HOOK_NAME,
    HOOK_TIMEOUT_MS,
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


class GeminiPlatform(Platform):
    name = PLATFORM_NAME
    display_name = DISPLAY_NAME

    def __init__(self, settings_file: Path | None = None) -> None:
        self._settings_file = settings_file or SETTINGS_FILE

    def install(self) -> None:
        settings = _load(self._settings_file)
        hooks = settings.setdefault("hooks", {})

        for event, script in HOOK_EVENTS.items():
            cmd = _resolve_command(script)
            blocks: list = hooks.setdefault(event, [])
            # Filter out any existing block that contains our hook name
            blocks[:] = [
                block
                for block in blocks
                if not any(h.get("name") == HOOK_NAME for h in block.get("hooks", []))
            ]
            # Append our block
            blocks.append(
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "name": HOOK_NAME,
                            "command": cmd,
                            "timeout": HOOK_TIMEOUT_MS,
                        }
                    ],
                }
            )

        _save(self._settings_file, settings)

    def uninstall(self) -> None:
        if not self._settings_file.exists():
            return

        settings = _load(self._settings_file)
        hooks = settings.get("hooks")
        if not hooks:
            if not settings:
                self._settings_file.unlink(missing_ok=True)
            return

        for event in list(hooks.keys()):
            blocks = hooks[event]
            blocks[:] = [
                block
                for block in blocks
                if not any(h.get("name") == HOOK_NAME for h in block.get("hooks", []))
            ]
            if not blocks:
                del hooks[event]

        if not hooks:
            del settings["hooks"]

        _save(self._settings_file, settings)
