# Token Use Analysis

Measure and compare token consumption across sessions.

## Session-level stats

```bash
thirdeye stats <session-prefix>      # input/output/cache tokens for a session
thirdeye stats                       # aggregate across all sessions
```

## Compare sessions

Run `thirdeye stats` on two sessions and compare `input_tokens`, `output_tokens`,
and `cache_read_input_tokens` to understand cost differences.

## Identify expensive turns

```bash
thirdeye events <sid> --type message  # list message events with token counts
thirdeye event <sid> <seq>            # full detail on one turn
```
