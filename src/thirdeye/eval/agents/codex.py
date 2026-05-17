from __future__ import annotations

import json
from typing import Any

from thirdeye.eval.agents.base import AgentAdapter, AgentConfig, OutputFormat


class CodexAdapter(AgentAdapter):
    """Adapter for the OpenAI Codex CLI.

    Uses ``codex exec --sandbox read-only --json {prompt}`` for
    non-interactive read-only execution with NDJSON output. The final
    assistant message event carries the response; cost is not reliably
    exposed today, so the returned cost dict is empty.
    """

    name = "codex"

    def __init__(self) -> None:
        self.config = AgentConfig(
            command="codex",
            args=["exec", "--sandbox", "read-only", "--json", "{prompt}"],
            output_format=OutputFormat.JSON,
            json_result_key="result",
            json_cost_key="cost_usd",
        )

    def parse_output(self, raw: str) -> tuple[str, dict[str, Any]]:
        """Codex emits NDJSON — one event per line. Return the last
        assistant message's content."""
        last_message = ""
        for line in raw.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            if (
                isinstance(ev, dict)
                and ev.get("type") == "message"
                and ev.get("role") == "assistant"
            ):
                content = ev.get("content", "")
                if isinstance(content, str):
                    last_message = content
        return (last_message or raw.strip(), {})
