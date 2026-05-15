# Token use analysis

Understand where tokens went in a single session and compare across sessions.

## Stats

```bash
thirdeye stats                # global totals across every recorded session
thirdeye stats <sid>          # per-session totals
```

Stats summarize input tokens, output tokens, and cache reads/writes where the
platform reports them.

## Discover available fields

Token-related field names vary by platform and evolve over time. Inspect one
event to see what's actually on disk before writing a `jq` query:

```bash
thirdeye event <sid> 0 --json
thirdeye event <sid> 0 --field data
```

Common fields to look for (presence depends on platform):

- `usage.input_tokens`, `usage.output_tokens`
- `usage.cache_creation_input_tokens`, `usage.cache_read_input_tokens`
- `model` (different models cost differently)

## Find high-cost sessions

Event count is a cheap proxy for cost; combine it with `stats` to drill in:

```bash
# Sessions with > 200 events since May 1
thirdeye list --json --since 2026-05-01 \
  | jq 'select(.event_count > 200) | .session_id' -r

# Then inspect totals for each candidate
for sid in $(thirdeye list --json --since 2026-05-01 \
              | jq -r 'select(.event_count > 200) | .session_id'); do
  echo "=== $sid ==="
  thirdeye stats "$sid"
done
```

## Cached vs fresh

Cache hits surface on individual events. Compute hit ratio with `jq` over the
event stream:

```bash
thirdeye events <sid> --json \
  | jq -s '
      map(.data.usage // empty)
      | {
          input:        ([.[] | .input_tokens // 0]                | add),
          cached_read:  ([.[] | .cache_read_input_tokens // 0]     | add),
          cache_write:  ([.[] | .cache_creation_input_tokens // 0] | add),
          output:       ([.[] | .output_tokens // 0]               | add),
        }
      | .cache_hit_ratio = (.cached_read / (.input + .cached_read + 0.0001))'
```

Compare the ratio across two sessions to see whether caching is being exercised
effectively.

## What to look for

When a session is unexpectedly expensive, scan for:

- **Runaway tool-result payloads.** A single tool returning hundreds of KB
  (e.g. `cat` on a giant file, an MCP call that didn't paginate) shows up as a
  large `output_tokens` jump on the next model turn.
  ```bash
  thirdeye events <sid> --type tool_result --json \
    | jq 'select((.data.content | tostring | length) > 20000)
          | {seq, name: .data.name, bytes: (.data.content | tostring | length)}'
  ```
- **Repeated re-reads of the same file.** The agent re-reading the same path
  three or more times suggests it lost context — tighten the prompt or use
  caching.
  ```bash
  thirdeye events <sid> --type tool_use --json \
    | jq -r 'select(.data.name == "Read") | .data.input.file_path' \
    | sort | uniq -c | sort -rn | head
  ```
- **Oversized system prompts.** The first model turn carries the system prompt;
  if `input_tokens` on `seq 0` (or the first message event) is unusually high,
  the system prompt itself is the issue.
