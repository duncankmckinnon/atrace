from __future__ import annotations

from pathlib import Path

PLATFORM_NAME = "codex"
DISPLAY_NAME = "Codex CLI"
CODEX_CONFIG_DIR = Path.home() / ".codex"
CODEX_CONFIG_FILE = CODEX_CONFIG_DIR / "config.toml"
NOTIFY_BIN_NAME = "thirdeye-codex-notify"
