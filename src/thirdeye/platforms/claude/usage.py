from __future__ import annotations

import json
from pathlib import Path

from thirdeye.paths import session_dir
from thirdeye.usage.errlog import log_capture_error, safe_capture
from thirdeye.usage.store import UsageStore
from thirdeye.usage.types import UsageRow


@safe_capture(phase="parse_transcript", platform="claude")
def capture_usage_claude(
    *,
    thirdeye_home: Path,
    session_id: str,
    transcript_path: str | None,
    triggering_seq: int,
) -> int:
    """Tail-parse the Claude transcript, append new UsageRows, advance offset.

    Returns the number of rows appended. Wrapped in @safe_capture so any error
    is logged to usage-errors.jsonl and the function returns None instead of
    raising.
    """
    if not transcript_path:
        return 0
    tp = Path(transcript_path)
    if not tp.is_file():
        log_capture_error(
            thirdeye_home=thirdeye_home,
            phase="open_source",
            message=f"transcript file does not exist: {transcript_path}",
            platform="claude",
            session_id=session_id,
            source_path=str(transcript_path),
        )
        return 0

    sd = session_dir(thirdeye_home, "claude", session_id)
    store = UsageStore(sd)
    state = store.read_state()
    offset = int(state.get("transcript_offset", 0))

    new_rows: list[UsageRow] = []
    with tp.open("rb") as f:
        f.seek(offset)
        for raw in f:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                frame = json.loads(line)
            except json.JSONDecodeError:
                continue
            row = _extract_row(frame, session_id, triggering_seq)
            if row is not None:
                new_rows.append(row)
        new_offset = f.tell()

    if new_rows:
        store.append(new_rows)
    store.write_state(
        transcript_offset=new_offset,
        last_seq=triggering_seq if new_rows else state.get("last_seq", -1),
    )
    return len(new_rows)


def _extract_row(frame: dict, session_id: str, triggering_seq: int) -> UsageRow | None:
    """Return a UsageRow if `frame` looks like an assistant turn with usage.

    Handles both nested (`frame["message"]["usage"]`) and flat
    (`frame["usage"]`) shapes.
    """
    if not isinstance(frame, dict):
        return None

    message = frame.get("message") if isinstance(frame.get("message"), dict) else None
    if message and "usage" in message:
        model = message.get("model") or frame.get("model")
        usage = message.get("usage") or {}
        ts = message.get("timestamp") or frame.get("timestamp") or ""
    elif "usage" in frame:
        model = frame.get("model")
        usage = frame.get("usage") or {}
        ts = frame.get("timestamp") or ""
    else:
        return None

    if not isinstance(usage, dict):
        return None
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if input_tokens is None or output_tokens is None or not model:
        return None

    total = int(input_tokens) + int(output_tokens)

    return UsageRow(
        session_id=session_id,
        seq=triggering_seq,
        ts=str(ts) if ts else "",
        platform="claude",
        model=str(model),
        input_tokens=int(input_tokens),
        output_tokens=int(output_tokens),
        total_tokens=total,
    )
