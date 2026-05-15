# Evaluation workflows

Grade agent behavior across a set of recorded sessions.

## The shape of an eval

Every evaluation has four phases:

1. **Select a population** — filter sessions by platform, cwd, time window, or tag.
2. **Define a rubric** — a yes/no (or scored) statement that can be checked
   against a session's events.
3. **Score each session** — walk events and emit a verdict.
4. **Aggregate** — tag verdicts back on the sessions so the population for
   the next iteration is filterable.

## Phase 1 — Select a population

```bash
# Every Claude session in this repo since April 1, tagged 'eval-set'
thirdeye list --json \
              --platform claude \
              --cwd "$PWD" \
              --since 2026-04-01 \
              --tag eval-set \
  | jq -r '.session_id'
```

Pipe the IDs to a scoring loop, or save them to a file:

```bash
thirdeye list --json --tag eval-set | jq -r '.session_id' > /tmp/eval_sids.txt
```

## Phase 2 — Define a rubric

Keep rubrics narrow and checkable from event data. Examples that work well:

- "The agent used `TodoWrite` when the task had ≥ 3 sub-steps."
- "The agent ran tests before claiming completion."
- "No tool calls returned `permission denied`."

## Phase 3 — Score sessions

Walk events with `thirdeye events <sid> --json` and pipe to a scoring script.
The script reads JSONL on stdin and writes a verdict line per session:

```bash
for sid in $(cat /tmp/eval_sids.txt); do
  verdict=$(thirdeye events "$sid" --json | python score_todowrite.py)
  echo "$sid $verdict"
done
```

### Pseudocode: TodoWrite-when-multi-step rubric

```python
# score_todowrite.py — read events JSONL from stdin, emit pass/fail
import json, sys

todo_writes = 0
user_prompt = ""

for line in sys.stdin:
    ev = json.loads(line)
    if ev.get("type") == "user_prompt_submit":
        user_prompt = ev["data"].get("prompt", "")
    if ev.get("type") == "tool_use" and ev["data"].get("name") == "TodoWrite":
        todo_writes += 1

# Heuristic: "do X, then Y, then Z" or numbered list signals multi-step
substeps = max(
    user_prompt.lower().count(" then "),
    sum(1 for line in user_prompt.splitlines() if line.strip()[:2] in ("1.","2.","3."))
)

if substeps >= 3 and todo_writes == 0:
    print("fail")
else:
    print("pass")
```

## Phase 4 — Aggregate via tags

Tag each session's first event with its verdict so populations are reusable:

```bash
while read -r sid verdict; do
  thirdeye tag "$sid" 0 --add "eval-todowrite-$verdict"
done < /tmp/scored.txt
```

Now the failure slice is one command away:

```bash
thirdeye list --tag eval-todowrite-fail
```

This becomes the population for the next iteration — investigate the failures,
adjust the prompt, re-run, re-score.

## Verify before reporting results

Before claiming a result, **manually inspect at least one passing and one failing
session** to confirm the heuristic is measuring what you think:

```bash
# Pick one of each
fail_sid=$(thirdeye list --tag eval-todowrite-fail --json | head -1 | jq -r '.session_id')
pass_sid=$(thirdeye list --tag eval-todowrite-pass --json | head -1 | jq -r '.session_id')

thirdeye events "$fail_sid" --type user_prompt_submit
thirdeye events "$fail_sid" --type tool_use --json | jq 'select(.data.name == "TodoWrite")'

thirdeye events "$pass_sid" --type user_prompt_submit
thirdeye events "$pass_sid" --type tool_use --json | jq 'select(.data.name == "TodoWrite")'
```

If the failing case actually had ≤ 2 sub-steps, the rubric is mis-classifying —
fix the heuristic before aggregating.
