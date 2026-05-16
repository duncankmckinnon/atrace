from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class UsageRow:
    """One row of model + token usage data, joinable back to events.alog by seq."""

    session_id: str
    seq: int
    ts: str
    platform: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> UsageRow:
        return cls(
            session_id=str(d["session_id"]),
            seq=int(d["seq"]),
            ts=str(d["ts"]),
            platform=str(d["platform"]),
            model=str(d["model"]),
            input_tokens=int(d["input_tokens"]),
            output_tokens=int(d["output_tokens"]),
            total_tokens=int(d["total_tokens"]),
        )
