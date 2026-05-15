from __future__ import annotations

import json
from pathlib import Path

import pytest

from thirdeye.paths import session_dir, usage_jsonl_path, usage_log_path
from thirdeye.platforms.gemini.usage import capture_usage_gemini


FIXTURE = Path(__file__).parent / "fixtures" / "usage" / "gemini_model_response.json"


def _payload() -> dict:
    return json.loads(FIXTURE.read_text())


def test_capture_from_real_payload(tmp_path: Path) -> None:
    rows = capture_usage_gemini(
        thirdeye_home=tmp_path,
        session_id="127de361",
        payload=_payload(),
        triggering_seq=5,
    )
    assert rows == 1
    line = json.loads(
        usage_jsonl_path(session_dir(tmp_path, "gemini", "127de361")).read_text().strip()
    )
    assert line["platform"] == "gemini"
    assert line["model"] == "gemini-3-flash-preview"
    assert line["input_tokens"] == 9582
    assert line["output_tokens"] == 1
    assert line["total_tokens"] == 9748
    assert line["seq"] == 5
    assert line["total_tokens"] != line["input_tokens"] + line["output_tokens"]


def test_capture_skips_empty_usage_metadata(tmp_path: Path) -> None:
    payload = _payload()
    payload["llm_response"]["usageMetadata"] = {}
    assert capture_usage_gemini(
        thirdeye_home=tmp_path, session_id="abc", payload=payload, triggering_seq=5
    ) == 0
    assert not usage_jsonl_path(session_dir(tmp_path, "gemini", "abc")).exists()


def test_capture_skips_zero_total_tokens(tmp_path: Path) -> None:
    payload = _payload()
    payload["llm_response"]["usageMetadata"] = {
        "promptTokenCount": 0, "candidatesTokenCount": 0, "totalTokenCount": 0
    }
    assert capture_usage_gemini(
        thirdeye_home=tmp_path, session_id="abc", payload=payload, triggering_seq=5
    ) == 0


def test_capture_uses_unknown_when_model_missing(tmp_path: Path) -> None:
    payload = _payload()
    payload["llm_request"].pop("model", None)
    rows = capture_usage_gemini(
        thirdeye_home=tmp_path, session_id="abc", payload=payload, triggering_seq=1
    )
    assert rows == 1
    line = json.loads(
        usage_jsonl_path(session_dir(tmp_path, "gemini", "abc")).read_text().strip()
    )
    assert line["model"] == "unknown"


def test_capture_no_llm_response(tmp_path: Path) -> None:
    rows = capture_usage_gemini(
        thirdeye_home=tmp_path,
        session_id="abc",
        payload={"session_id": "abc"},
        triggering_seq=1,
    )
    assert rows == 0


def test_safe_capture_swallows_unexpected_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import thirdeye.platforms.gemini.usage as mod
    original = mod.UsageStore

    class Boom(original):  # type: ignore[misc]
        def append(self, rows):
            raise RuntimeError("simulated")

    monkeypatch.setattr(mod, "UsageStore", Boom)
    result = capture_usage_gemini(
        thirdeye_home=tmp_path, session_id="abc", payload=_payload(), triggering_seq=1
    )
    assert result is None
    assert usage_log_path(tmp_path).exists()
