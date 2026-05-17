from __future__ import annotations

from thirdeye.eval.agents.base import AgentAdapter, AgentConfig, OutputFormat


class ClaudeAdapter(AgentAdapter):
    """Adapter for the Claude Code CLI.

    Uses ``claude -p {prompt}`` with ``--output-format json`` so we get a
    structured response carrying cost and usage. ``--allowedTools`` scopes
    the agent to read-only operations for safe evaluation.
    """

    name = "claude"
    ALLOWED_TOOLS = (
        "Bash(thirdeye *) Bash(sqlite3 *) Bash(jq *) Read Glob Grep"
    )

    def __init__(self) -> None:
        self.config = AgentConfig(
            command="claude",
            args=[
                "-p",
                "{prompt}",
                "--output-format",
                "json",
                "--allowedTools",
                self.ALLOWED_TOOLS,
            ],
            output_format=OutputFormat.JSON,
            json_result_key="result",
            json_cost_key="cost_usd",
        )
