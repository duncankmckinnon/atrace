from __future__ import annotations

import json
from pathlib import Path

import pytest

from thirdeye.eval.agents.base import (
    AgentAdapter,
    AgentConfig,
    ConfigAdapter,
    OutputFormat,
)


# --- AgentConfig ---

def test_config_defaults():
    c = AgentConfig(command="x", args=["{prompt}"])
    assert c.output_format == OutputFormat.TEXT
    assert c.json_result_key == "result"


def test_config_string_output_format_coerces():
    c = AgentConfig(command="x", args=["{prompt}"], output_format="json")
    assert c.output_format == OutputFormat.JSON


def test_config_rejects_empty_command():
    with pytest.raises(ValueError, match="command"):
        AgentConfig(command="", args=["{prompt}"])


def test_config_rejects_empty_args():
    with pytest.raises(ValueError, match="args"):
        AgentConfig(command="x", args=[])


def test_config_rejects_missing_prompt_placeholder():
    with pytest.raises(ValueError, match="prompt"):
        AgentConfig(command="x", args=["--no-prompt"])


def test_config_to_dict_text_omits_json_keys():
    c = AgentConfig(command="x", args=["{prompt}"])
    d = c.to_dict()
    assert "json_result_key" not in d
    assert d["output_format"] == "text"


def test_config_to_dict_json_includes_keys():
    c = AgentConfig(command="x", args=["{prompt}"], output_format="json",
                    json_result_key="foo", json_cost_key="bar")
    d = c.to_dict()
    assert d["json_result_key"] == "foo"
    assert d["json_cost_key"] == "bar"


def test_config_from_dict_uses_default_command_when_missing():
    c = AgentConfig.from_dict({"args": ["{prompt}"]}, default_command="x")
    assert c.command == "x"


# --- AgentAdapter (via ConfigAdapter) ---

def test_build_command_substitutes_prompt():
    c = ConfigAdapter(name="x", config=AgentConfig(command="x", args=["-p", "{prompt}"]))
    cmd = c.build_command("hello", Path("/tmp"))
    assert cmd == ["x", "-p", "hello"]


def test_build_command_with_extra_flags():
    c = ConfigAdapter(name="x", config=AgentConfig(
        command="x", args=["-p", "{prompt}", "--flag"]
    ))
    cmd = c.build_command("h", Path("/"))
    assert cmd == ["x", "-p", "h", "--flag"]


def test_parse_output_text_strips_whitespace():
    c = ConfigAdapter(name="x", config=AgentConfig(command="x", args=["{prompt}"]))
    text, cost = c.parse_output("  hello  \n")
    assert text == "hello"
    assert cost == {}


def test_parse_output_json_extracts_result_and_cost():
    c = ConfigAdapter(name="x", config=AgentConfig(
        command="x", args=["{prompt}"], output_format="json",
        json_result_key="result", json_cost_key="cost_usd",
    ))
    raw = json.dumps({"result": "the answer", "cost_usd": {"usd": 0.01}})
    text, cost = c.parse_output(raw)
    assert text == "the answer"
    assert cost == {"usd": 0.01}


def test_parse_output_json_falls_back_on_decode_error():
    c = ConfigAdapter(name="x", config=AgentConfig(
        command="x", args=["{prompt}"], output_format="json",
    ))
    text, cost = c.parse_output("not json")
    assert text == "not json"
    assert cost == {}


def test_parse_output_json_non_dict_cost_becomes_empty():
    c = ConfigAdapter(name="x", config=AgentConfig(
        command="x", args=["{prompt}"], output_format="json",
    ))
    raw = json.dumps({"result": "ok", "cost_usd": 42})  # cost not a dict
    text, cost = c.parse_output(raw)
    assert text == "ok"
    assert cost == {}


# --- ConfigAdapter.from_config ---

def test_config_adapter_from_yaml_entry():
    a = ConfigAdapter.from_config("myagent", {
        "command": "myagent",
        "args": ["-p", "{prompt}"],
        "output_format": "json",
    })
    assert a.name == "myagent"
    assert a.config.command == "myagent"
    assert a.config.output_format == OutputFormat.JSON
