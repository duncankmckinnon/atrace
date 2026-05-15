---
name: use-thirdeye
description: Use when working in a repo instrumented with thirdeye — tracing agentic CLI sessions, searching past sessions, retrieving events, analyzing token usage, and running evaluations.
---

# use-thirdeye

`thirdeye` (PyPI: `thrdi`) captures events from agentic CLI tools (Claude Code, Codex, Gemini CLI)
into a unified per-session event store. Use this skill to set up tracing, search past sessions,
debug tool calls, analyze token usage, and run evaluations on observed behavior.

## Sections

- [Setup and Tracing](references/setup-and-tracing.md) — install hooks and verify data is flowing
- [Searching and Retrieval](references/searching-and-retrieval.md) — find sessions and events
- [Tool Call Debugging](references/tool-call-debugging.md) — inspect tool inputs and outputs
- [Token Use Analysis](references/token-use-analysis.md) — measure and compare token consumption
- [Evaluation Workflows](references/evaluation-workflows.md) — run structured evaluations on traces
