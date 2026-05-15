# Searching and Retrieval

Find sessions and events across the unified store.

## List sessions

```bash
thirdeye list                        # all platforms, newest first
thirdeye list --platform claude      # filter by platform
thirdeye list --since "1 hour ago"   # sessions active in the last hour
```

## Search across sessions

```bash
thirdeye search "keyword"            # full-text search over event content
thirdeye search "keyword" --platform claude
```

## Retrieve a specific event

```bash
thirdeye event <session-prefix> <seq>
thirdeye show <session-prefix>       # summary of a session
```

## Tail recent events

```bash
thirdeye tail <session-prefix>       # last 10 events in a session
thirdeye tail <session-prefix> -n 20 # last 20 events
```
