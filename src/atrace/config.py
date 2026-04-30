from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def default_root() -> Path:
    env = os.environ.get("ATRACE_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".atrace"


@dataclass(frozen=True)
class Config:
    root: Path

    @property
    def traces_dir(self) -> Path:
        return self.root / "traces"

    @property
    def config_file(self) -> Path:
        return self.root / "config.yaml"


def load() -> Config:
    return Config(root=default_root())
