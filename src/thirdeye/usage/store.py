from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from thirdeye.paths import usage_jsonl_path, usage_state_path
from thirdeye.usage.types import UsageRow


class UsageStore:
    """Sidecar I/O for one session directory.

    Owns two files:
    - usage.jsonl   — append-only, one UsageRow per line
    - usage.state.json — small JSON blob with capture bookmarks
    """

    def __init__(self, session_dir_: Path) -> None:
        self.session_dir = session_dir_

    @property
    def jsonl_path(self) -> Path:
        return usage_jsonl_path(self.session_dir)

    @property
    def state_path(self) -> Path:
        return usage_state_path(self.session_dir)

    def append(self, rows: list[UsageRow]) -> None:
        """Append rows to usage.jsonl. Atomic at the line level via O_APPEND."""
        if not rows:
            return
        self.session_dir.mkdir(parents=True, exist_ok=True)
        with self.jsonl_path.open("a", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row.to_dict(), separators=(",", ":")) + "\n")

    def iter_rows(self) -> Iterator[UsageRow]:
        """Yield rows from usage.jsonl. Skips empty / malformed lines silently."""
        if not self.jsonl_path.exists():
            return
        with self.jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield UsageRow.from_dict(json.loads(line))
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

    def read_state(self) -> dict[str, Any]:
        """Read usage.state.json. Returns {} if missing or malformed."""
        if not self.state_path.exists():
            return {}
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def write_state(self, **fields: Any) -> None:
        """Merge fields into usage.state.json. Atomic via tmp + rename."""
        current = self.read_state()
        current.update(fields)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(current, separators=(",", ":")), encoding="utf-8")
        os.replace(tmp, self.state_path)
