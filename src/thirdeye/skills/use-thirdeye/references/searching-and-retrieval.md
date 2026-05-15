# Searching and Retrieval

Find sessions and events across the unified store.

## List sessions

```bash
thirdeye sessions                    # all platforms, newest first
thirdeye sessions --platform claude  # filter by platform
thirdeye sessions --limit 10
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

## Tail live events

```bash
thirdeye tail <session-prefix>       # stream events as they arrive
```
