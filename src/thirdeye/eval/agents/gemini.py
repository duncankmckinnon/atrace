from __future__ import annotations

from thirdeye.eval.agents.base import AgentAdapter, AgentConfig, OutputFormat


class GeminiAdapter(AgentAdapter):
    """Adapter for the Gemini CLI.

    Uses ``gemini -p {prompt} --output-format json --approval-mode plan``
    for non-interactive read-only execution. Plan mode is documented as
    read-only and prevents file mutations.
    """

    name = "gemini"

    def __init__(self) -> None:
        self.config = AgentConfig(
            command="gemini",
            args=[
                "-p",
                "{prompt}",
                "--output-format",
                "json",
                "--approval-mode",
                "plan",
            ],
            output_format=OutputFormat.JSON,
            json_result_key="response",
            json_cost_key="stats",
        )
