from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any

VALID_VERDICTS = frozenset({"pass", "warn", "fail", "unknown"})
VALID_SEVERITIES = frozenset({"info", "warn", "error"})


@dataclass(frozen=True)
class Finding:
    seq: int | None  # event seq this finding anchors to, or None
    severity: str  # "info" | "warn" | "error"
    note: str
    category: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq,
            "severity": self.severity,
            "category": self.category,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Finding:
        sev = str(d.get("severity", "info"))
        if sev not in VALID_SEVERITIES:
            sev = "info"
        seq = d.get("seq")
        return cls(
            seq=int(seq) if seq is not None else None,
            severity=sev,
            note=str(d.get("note", "")),
            category=str(d.get("category", "")),
        )


@dataclass(frozen=True)
class EvalResult:
    id: str
    session_id: str
    definition: str
    agent: str
    agent_model: str
    agent_session_id: str | None
    started_at: str
    ended_at: str
    duration_ms: int
    verdict: str  # "pass" | "warn" | "fail" | "unknown"
    summary: str
    scores: dict[str, float] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    markdown: str = ""
    cost: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # asdict converts Findings to plain dicts via dataclass introspection
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EvalResult:
        verdict = str(d.get("verdict", "unknown"))
        if verdict not in VALID_VERDICTS:
            verdict = "unknown"
        return cls(
            id=str(d["id"]),
            session_id=str(d["session_id"]),
            definition=str(d["definition"]),
            agent=str(d["agent"]),
            agent_model=str(d.get("agent_model", "")),
            agent_session_id=d.get("agent_session_id"),
            started_at=str(d["started_at"]),
            ended_at=str(d["ended_at"]),
            duration_ms=int(d.get("duration_ms", 0)),
            verdict=verdict,
            summary=str(d.get("summary", "")),
            scores={str(k): float(v) for k, v in (d.get("scores") or {}).items()},
            findings=[Finding.from_dict(f) for f in (d.get("findings") or [])],
            markdown=str(d.get("markdown", "")),
            cost=dict(d.get("cost") or {}),
        )


_JSON_FENCE_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


def parse_envelope(agent_text: str) -> tuple[dict[str, Any] | None, str]:
    """Extract the first ```json fenced block from `agent_text`.

    Returns (envelope_dict | None, narrative_markdown). On failure to parse
    JSON, returns (None, agent_text).
    """
    if not agent_text:
        return None, ""
    match = _JSON_FENCE_RE.search(agent_text)
    if match is None:
        return None, agent_text
    try:
        envelope = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None, agent_text
    narrative = (agent_text[: match.start()] + agent_text[match.end() :]).strip()
    return envelope, narrative
