# thirdeye

Trace every agent session on your machine — Claude Code, Cursor, Codex, Gemini, Copilot — into one history you and your agents can search.

## Install

```bash
pipx install thrdi        # or: uv tool install thrdi
```

## Enable tracing

```bash
thirdeye add --claude        # also: --cursor, --codex, --gemini, --copilot
```

To detach: `thirdeye add --claude --remove`.

## Read your history

```bash
thirdeye list                          # every session, every platform
thirdeye events <id>                   # one session, terse
thirdeye tail <id> -n 5                # last few events
thirdeye event <id> <seq>              # one event, fully expanded
thirdeye search "migration"            # substring across all sessions
thirdeye stats                         # totals
```

Add `--json` for parseable JSONL, `--tree` for human-readable, `--platform` / `--cwd` to filter. Session IDs accept any unique prefix. Run `thirdeye --help` for the full reference.

## License

MIT.
