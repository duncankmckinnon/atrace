# Setup and Tracing

Install thirdeye and register hooks so events are captured automatically.

## Install

```bash
pip install thrdi
# or
brew install duncankmckinnon/tap/thirdeye
```

## Register Claude Code hooks

```bash
thirdeye install claude
```

This writes hook entries into `.claude/settings.json` so every Claude Code session
is captured under `<thirdeye_home>/traces/claude/<session-id>/`.

## Verify data is flowing

```bash
thirdeye sessions          # list recent sessions
thirdeye events <sid>      # list events in a session
```
