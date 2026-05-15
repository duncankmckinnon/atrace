# Evaluation Workflows

Run structured evaluations on observed behavior captured in thirdeye traces.

## Export a session for evaluation

```bash
thirdeye events <sid> --json > session_events.jsonl
```

Each line is a JSON object with `seq`, `type`, `timestamp`, and `data` fields.

## Tag ground-truth events

Use `thirdeye tag` to mark events that represent correct or incorrect behavior:

```bash
thirdeye tag <sid> <seq> --add "correct"
thirdeye tag <sid> <seq> --add "incorrect"
```

Then export tagged events:

```bash
thirdeye search "" --tag correct   # retrieve all events tagged "correct"
```

## Ingest external evaluation results

```bash
thirdeye ingest <file>          # add evaluation output back into the store
```

This lets you correlate model-graded results with the original trace events.
