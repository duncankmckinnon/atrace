# thirdeye

[![PyPI](https://img.shields.io/pypi/v/thrdi.svg)](https://pypi.org/project/thrdi/)
[![Homebrew](https://img.shields.io/badge/homebrew-duncankmckinnon%2Ftap-orange)](https://github.com/duncankmckinnon/homebrew-tap)
[![CI](https://github.com/duncankmckinnon/thirdeye/actions/workflows/test.yml/badge.svg)](https://github.com/duncankmckinnon/thirdeye/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/duncankmckinnon/thirdeye/branch/main/graph/badge.svg)](https://codecov.io/gh/duncankmckinnon/thirdeye)
[![Python](https://img.shields.io/pypi/pyversions/thrdi.svg)](https://pypi.org/project/thrdi/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Trace every agent session on your machine — Claude Code, Cursor, Codex, Gemini, Copilot — into one history you and your agents can search.

## Install

```bash
brew install duncankmckinnon/tap/thirdeye    # macOS / Linux
pipx install thrdi                           # or: uv tool install thrdi
```

## Enable tracing

```bash
thirdeye add --claude        # also: --cursor, --codex, --gemini, --copilot
```

To detach: `thirdeye remove --claude`.

## Read your history

```bash
thirdeye list                          # every session, every platform
thirdeye events <id>                   # one session, terse
thirdeye tail <id> -n 5                # last few events
thirdeye event <id> <seq>              # one event, fully expanded
thirdeye search "migration"            # substring across all sessions
thirdeye stats                         # totals
```

## Tag and filter

```bash
thirdeye tag <id> <seq> --add bug,review     # tag an event
thirdeye tag <id> --list                     # list tagged events in a session
thirdeye tag <id> <seq> --remove bug         # untag
thirdeye tags                                # global tag inventory
thirdeye search "migration" --tag review --platform claude --since 2026-05-01
```

Add `--json` for parseable JSONL, `--tree` for human-readable, `--platform` / `--cwd` / `--tag` / `--since` / `--until` to filter. Session IDs accept any unique prefix. Run `thirdeye --help` for the full reference.

## License

MIT.
