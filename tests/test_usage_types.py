from __future__ import annotations

import json

import pytest

from thirdeye.usage.types import UsageRow


def make_row(**overrides) -> UsageRow:
    defaults = dict(
        session_id="abc123",
        seq=0,
        ts="2026-05-15T00:00:00.000Z",
        platform="claude",
        model="claude-opus-4-7",
        input_tokens=100,
        output_tokens=10,
        total_tokens=110,
    )
    defaults.update(overrides)
    return UsageRow(**defaults)


def test_round_trip_via_dict() -> None:
    row = make_row()
    assert UsageRow.from_dict(row.to_dict()) == row


def test_round_trip_via_json() -> None:
    row = make_row()
    encoded = json.dumps(row.to_dict())
    decoded = UsageRow.from_dict(json.loads(encoded))
    assert decoded == row


def test_from_dict_coerces_string_numerics() -> None:
    """Integer-like strings should coerce, mirroring JSON-from-disk quirks."""
    row = UsageRow.from_dict(
        {
            "session_id": "abc",
            "seq": "5",
            "ts": "2026-05-15T00:00:00Z",
            "platform": "claude",
            "model": "m",
            "input_tokens": "100",
            "output_tokens": "10",
            "total_tokens": "110",
        }
    )
    assert row.seq == 5 and row.input_tokens == 100


def test_from_dict_missing_field_raises() -> None:
    with pytest.raises(KeyError):
        UsageRow.from_dict({"session_id": "abc"})


def test_is_frozen() -> None:
    row = make_row()
    with pytest.raises(Exception):  # FrozenInstanceError, but version-dependent
        row.seq = 99  # type: ignore[misc]


def test_equality_value_based() -> None:
    assert make_row() == make_row()
    assert make_row(seq=1) != make_row(seq=2)
