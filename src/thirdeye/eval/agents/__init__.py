from __future__ import annotations

from pathlib import Path

from thirdeye.eval.agents.base import AgentAdapter, AgentConfig, ConfigAdapter, OutputFormat
from thirdeye.eval.agents.claude import ClaudeAdapter
from thirdeye.eval.agents.codex import CodexAdapter
from thirdeye.eval.agents.gemini import GeminiAdapter

_BUILTIN_ADAPTERS: dict[str, type[AgentAdapter]] = {
    "claude": ClaudeAdapter,
    "codex": CodexAdapter,
    "gemini": GeminiAdapter,
}


def get_adapter(name: str, *, thirdeye_home: Path | None = None) -> AgentAdapter:
    """Return an adapter instance by name.

    Raises ValueError for an unknown agent name. ``thirdeye_home`` is reserved
    for loading user-defined adapters from ``eval-agents.yaml``; not consulted
    yet.
    """
    cls = _BUILTIN_ADAPTERS.get(name)
    if cls is None:
        raise ValueError(
            f"unknown agent {name!r}; known: {sorted(_BUILTIN_ADAPTERS)}"
        )
    return cls()


__all__ = [
    "AgentAdapter",
    "AgentConfig",
    "ConfigAdapter",
    "OutputFormat",
    "ClaudeAdapter",
    "CodexAdapter",
    "GeminiAdapter",
    "get_adapter",
]
