from __future__ import annotations

import re
import shutil
from pathlib import Path

from thirdeye.platforms.base import Platform
from thirdeye.platforms.codex.constants import (
    CODEX_CONFIG_FILE,
    DISPLAY_NAME,
    NOTIFY_BIN_NAME,
    PLATFORM_NAME,
)

_NOTIFY_LINE_RE = re.compile(r"^notify\s*=\s*(\[.*?\])\s*$", re.MULTILINE | re.DOTALL)


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text()
    except OSError:
        return ""


def _parse_notify_array(value: str) -> list[str]:
    """Parse a TOML inline array like ['a', "b"] -> ['a', 'b']."""
    items: list[str] = []
    for m in re.finditer(r'"([^"]*)"|\'([^\']*)\'', value):
        items.append(m.group(1) if m.group(1) is not None else m.group(2))
    return items


def _format_notify_array(items: list[str]) -> str:
    quoted = ", ".join("'" + item.replace("'", "\\'") + "'" for item in items)
    return f"notify = [{quoted}]"


class CodexPlatform(Platform):
    name = PLATFORM_NAME
    display_name = DISPLAY_NAME

    def __init__(self, config_file: Path | None = None) -> None:
        self._config_file = config_file or CODEX_CONFIG_FILE

    def install(self) -> None:
        cmd = shutil.which(NOTIFY_BIN_NAME) or NOTIFY_BIN_NAME
        text = _read_text(self._config_file)
        match = _NOTIFY_LINE_RE.search(text)
        if match:
            existing = _parse_notify_array(match.group(1))
            if cmd in existing:
                return
            items = existing + [cmd]
            new_line = _format_notify_array(items)
            new_text = text[: match.start()] + new_line + text[match.end() :]
        else:
            notify_line = _format_notify_array([cmd]) + "\n"
            # Insert before first section header to keep it top-level
            section_match = re.search(r"^\[", text, re.MULTILINE)
            if text and section_match:
                insert_pos = section_match.start()
                new_text = text[:insert_pos] + notify_line + "\n" + text[insert_pos:]
            else:
                prefix = text + ("\n" if text and not text.endswith("\n") else "")
                new_text = prefix + notify_line
        self._config_file.parent.mkdir(parents=True, exist_ok=True)
        self._config_file.write_text(new_text)

    def uninstall(self) -> None:
        text = _read_text(self._config_file)
        if not text:
            return
        cmd_to_remove = shutil.which(NOTIFY_BIN_NAME) or NOTIFY_BIN_NAME
        match = _NOTIFY_LINE_RE.search(text)
        if not match:
            return
        existing = _parse_notify_array(match.group(1))
        filtered = [
            x
            for x in existing
            if x not in (cmd_to_remove, NOTIFY_BIN_NAME) and Path(x).name != NOTIFY_BIN_NAME
        ]
        if filtered == existing:
            return
        if not filtered:
            # Remove the entire notify line (and one trailing newline)
            start = match.start()
            end = match.end()
            if end < len(text) and text[end] == "\n":
                end += 1
            new_text = text[:start] + text[end:]
        else:
            new_line = _format_notify_array(filtered)
            new_text = text[: match.start()] + new_line + text[match.end() :]
        if not new_text.strip():
            if self._config_file.exists():
                self._config_file.unlink()
            return
        self._config_file.write_text(new_text)
