# Tool Call Debugging

Inspect tool inputs and outputs recorded in a session.

## Find tool-use events

```bash
thirdeye search "tool_use"           # search for tool_use events across all sessions
thirdeye events <sid> --type tool_use
```

## Inspect a specific tool call

```bash
thirdeye event <sid> <seq>
```

The output includes the tool name, input parameters, and (for `tool_result` events)
the response content and any error.

## Tag events for later review

```bash
thirdeye tag <sid> <seq> --add "needs-review,slow"
thirdeye tag <sid> --list   # see all tagged events in session
```
