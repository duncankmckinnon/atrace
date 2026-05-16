from __future__ import annotations

from pathlib import Path

from thirdeye.paths import session_dir
from thirdeye.usage.errlog import safe_capture
from thirdeye.usage.store import UsageStore
from thirdeye.usage.types import UsageRow


@safe_capture(phase="extract_usage", platform="gemini")
def capture_usage_gemini(
    *,
    thirdeye_home: Path,
    session_id: str,
    payload: dict,
    triggering_seq: int,
) -> int:
    """Build one UsageRow from a Gemini after_model payload, append it.

    Returns 1 if a row was appended, 0 if the payload had no usable usage
    (e.g. an intermediate reasoning pass with empty usageMetadata).
    """
    llm_response = payload.get("llm_response") if isinstance(payload, dict) else None
    if not isinstance(llm_response, dict):
        return 0
    usage_meta = llm_response.get("usageMetadata")
    if not isinstance(usage_meta, dict):
        return 0
    total = usage_meta.get("totalTokenCount")
    if not total:
        return 0

    llm_request = payload.get("llm_request") if isinstance(payload, dict) else None
    model = ""
    if isinstance(llm_request, dict):
        model = str(llm_request.get("model") or "")
    if not model:
        model = "unknown"

    row = UsageRow(
        session_id=session_id,
        seq=triggering_seq,
        ts=str(payload.get("timestamp") or ""),
        platform="gemini",
        model=model,
        input_tokens=int(usage_meta.get("promptTokenCount", 0)),
        output_tokens=int(usage_meta.get("candidatesTokenCount", 0)),
        total_tokens=int(total),
    )

    sd = session_dir(thirdeye_home, "gemini", session_id)
    store = UsageStore(sd)
    store.append([row])
    store.write_state(last_seq=triggering_seq)
    return 1
