# atrace

Trace every agent session on your machine — Claude Code, Cursor, Codex, Gemini, Copilot — into one history you and your agents can search.

## Install

```bash
pipx install atrace        # or: uv tool install atrace
```

## Enable tracing

```bash
atrace add --claude        # also: --cursor, --codex, --gemini, --copilot
```

To detach: `atrace add --claude --remove`.

## Read your history

```bash
atrace list                          # every session, every platform
atrace events <id>                   # one session, terse
atrace tail <id> -n 5                # last few events
atrace event <id> <seq>              # one event, fully expanded
atrace search "migration"            # substring across all sessions
atrace stats                         # totals
```

Add `--json` for parseable JSONL, `--tree` for human-readable, `--platform` / `--cwd` to filter. Session IDs accept any unique prefix. Run `atrace --help` for the full reference.

## License

MIT.
