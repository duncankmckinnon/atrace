# Tool call debugging

Use this workflow when a past agent ran a tool that failed, hung, or returned
wrong data. The goal is to locate the offending event and reconstruct the tool's
exact input and output.

## Five-step workflow

### 1. Locate the session

Narrow by platform, cwd, and time window first:

```bash
thirdeye list --platform claude \
              --cwd /path/to/repo \
              --since 2026-05-01
```

If you don't already know the session, search for a fragment of the tool name
or the error message:

```bash
thirdeye search "old_string not found" --platform claude
```

### 2. Inspect the session timeline

Confirm the event schema by expanding one event first — the field names are
authoritative on disk and may differ from documentation:

```bash
thirdeye event <sid> 0 --json
```

Then filter to tool-call events:

```bash
thirdeye events <sid> --type tool_use --json
thirdeye events <sid> --type tool_result --json
```

For more precise filtering, combine `--json` with `jq`:

```bash
thirdeye events <sid> --json \
  | jq 'select(.type == "tool_use" and .data.name == "Edit")'
```

### 3. Expand the offending event

Once you've identified the `seq` of the suspect event:

```bash
thirdeye event <sid> <seq>
thirdeye event <sid> <seq> --field input    # just the input field of data
```

### 4. Tag the event for follow-up

```bash
thirdeye tag <sid> <seq> --add bug,tool-error
thirdeye tag <sid> --list                   # confirm what's tagged in this session
```

### 5. Find recurrences across sessions

```bash
thirdeye search "old_string not found" --tag tool-error --json \
  | jq -r '.session_id' | sort -u
```

## Concrete example — "Edit failed: old_string not found"

The agent's `Edit` tool reports `old_string not found in <file>`. Find the call:

```bash
# 1. Search for the error fragment
thirdeye search "old_string not found" --platform claude --since 2026-05-10

# Output points at session 7f3e4c21..., seq 42.

# 2. Pull the Edit tool_use and its tool_result side-by-side
thirdeye event 7f3e4c21 42                     # the Edit tool_use
thirdeye event 7f3e4c21 43                     # the matching tool_result

# 3. Just the input (the offending old_string)
thirdeye event 7f3e4c21 42 --field input

# 4. Tag for follow-up and find recurrences
thirdeye tag 7f3e4c21 42 --add tool-error,edit-mismatch
thirdeye search "old_string not found" --tag tool-error
```

## Common signatures

| Symptom                            | Suggested query                                              |
| ---------------------------------- | ------------------------------------------------------------ |
| `Edit` mismatch                    | `thirdeye search "old_string not found"`                     |
| Sandbox / permission failure       | `thirdeye search "permission denied"`                        |
| Tool hang / wall-clock exceeded    | `thirdeye search "timeout"`                                  |
| Schema mismatch on tool input      | `thirdeye search "InputValidationError"`                     |
| Bash command not found             | `thirdeye search "command not found"`                        |
| MCP tool unreachable               | `thirdeye search "mcp" --tag tool-error`                     |
