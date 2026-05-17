from __future__ import annotations

import json
from pathlib import Path

from thirdeye.eval.agents.base import OutputFormat
from thirdeye.eval.agents.gemini import GeminiAdapter


def test_name():
    assert GeminiAdapter().name == "gemini"


def test_config_is_json_output():
    a = GeminiAdapter()
    assert a.config.output_format == OutputFormat.JSON
    assert a.config.command == "gemini"


def test_build_command_uses_plan_mode():
    cmd = GeminiAdapter().build_command("evaluate", Path("/"))
    assert cmd[0] == "gemini"
    assert "-p" in cmd
    assert "evaluate" in cmd
    assert "--approval-mode" in cmd
    assert "plan" in cmd
    assert "--output-format" in cmd
    assert "json" in cmd


def test_build_command_does_not_use_yolo():
    """Eval agent must NOT run with yolo / auto_edit approval modes."""
    cmd = GeminiAdapter().build_command("x", Path("/"))
    assert "yolo" not in cmd
    assert "auto_edit" not in cmd
    assert "--yolo" not in cmd


def test_parse_output_extracts_response_and_stats():
    raw = json.dumps({
        "response": "the agent's reply",
        "stats": {"promptTokenCount": 1000, "candidatesTokenCount": 50},
    })
    text, cost = GeminiAdapter().parse_output(raw)
    assert text == "the agent's reply"
    assert cost == {"promptTokenCount": 1000, "candidatesTokenCount": 50}


def test_parse_output_falls_back_on_malformed_json():
    text, cost = GeminiAdapter().parse_output("not json")
    assert text == "not json"
    assert cost == {}


def test_parse_output_missing_response_key():
    raw = json.dumps({"stats": {"x": 1}})
    text, cost = GeminiAdapter().parse_output(raw)
    # Falls back to raw when `response` is absent (per AgentAdapter default)
    assert text == raw
    assert cost == {"x": 1}
