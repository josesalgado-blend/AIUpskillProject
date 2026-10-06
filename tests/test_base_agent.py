# tests/test_base_agent.py
"""BaseAgent internals with a fake `completion` (no network, no quota)."""

import json
import time
from types import SimpleNamespace

import pytest

import src.agents.base_agent as base_agent
from src.agents.base_agent import BaseAgent


class _Agent(BaseAgent):
    async def _load_context(self, input_path):
        return {}

    async def _process(self, context):
        return {}

    async def _save_result(self, result, output_path):
        pass


def _text(content):
    message = SimpleNamespace(content=content, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _tool_call(name, arguments, call_id="call_1"):
    function = SimpleNamespace(name=name, arguments=json.dumps(arguments))
    message = SimpleNamespace(
        content=None,
        tool_calls=[SimpleNamespace(id=call_id, function=function)],
        model_dump=lambda: {"role": "assistant", "content": None},
    )
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_requires_a_model(monkeypatch):
    monkeypatch.delenv("LITELLM_MODEL", raising=False)
    with pytest.raises(ValueError, match="No model configured"):
        _Agent()


def test_settings_from_env_and_constructor(monkeypatch):
    monkeypatch.setenv("LITELLM_MODEL", "x/y")
    monkeypatch.setenv("LLM_NUM_RETRIES", "5")
    monkeypatch.setenv("LLM_MIN_INTERVAL", "1.5")

    from_env = _Agent()
    assert (from_env.model, from_env.num_retries, from_env.min_interval) == (
        "x/y",
        5,
        1.5,
    )

    explicit = _Agent(model="a/b", num_retries=0, min_interval=0)
    assert (explicit.model, explicit.num_retries, explicit.min_interval) == (
        "a/b",
        0,
        0,
    )


def test_call_llm_passes_retries_and_system_prompt(monkeypatch):
    seen = {}

    def fake_completion(**kwargs):
        seen.update(kwargs)
        return _text("hola")

    monkeypatch.setattr(base_agent, "completion", fake_completion)
    agent = _Agent(model="x/y", num_retries=4, min_interval=0)

    assert agent._call_llm("question", system="be brief") == "hola"
    assert seen["num_retries"] == 4
    assert [m["role"] for m in seen["messages"]] == ["system", "user"]


def test_call_llm_reraises_provider_errors(monkeypatch):
    def failing_completion(**kwargs):
        raise RuntimeError("429")

    monkeypatch.setattr(base_agent, "completion", failing_completion)

    with pytest.raises(RuntimeError, match="429"):
        _Agent(model="x/y", min_interval=0)._call_llm("q")


def test_throttle_keeps_min_interval(monkeypatch):
    monkeypatch.setattr(base_agent, "completion", lambda **kw: _text("ok"))
    agent = _Agent(model="x/y", min_interval=0.15)

    agent._call_llm("one")
    start = time.monotonic()
    agent._call_llm("two")

    assert time.monotonic() - start >= 0.1


def test_tool_loop_executes_tool_then_returns_text(monkeypatch):
    responses = iter([_tool_call("add", {"a": 2, "b": 3}), _text("the sum is 5")])
    sent = []

    def fake_completion(**kwargs):
        sent.append([dict(m) for m in kwargs["messages"]])
        return next(responses)

    monkeypatch.setattr(base_agent, "completion", fake_completion)
    agent = _Agent(model="x/y", tools=[{"type": "function"}], min_interval=0)
    agent.register_tool_function("add", lambda a, b: {"result": a + b})

    assert agent._call_llm_with_tools("2+3?") == "the sum is 5"
    tool_message = sent[1][-1]  # what the model received on the second round
    assert tool_message["role"] == "tool"
    assert json.loads(tool_message["content"]) == {"result": 5}


def test_tool_loop_rejects_unregistered_tools(monkeypatch):
    monkeypatch.setattr(
        base_agent, "completion", lambda **kw: _tool_call("missing", {})
    )
    agent = _Agent(model="x/y", min_interval=0)

    with pytest.raises(ValueError, match="not registered"):
        agent._call_llm_with_tools("q")


def test_tool_loop_stops_after_ten_rounds(monkeypatch):
    monkeypatch.setattr(base_agent, "completion", lambda **kw: _tool_call("noop", {}))
    agent = _Agent(model="x/y", min_interval=0)
    agent.register_tool_function("noop", lambda: {})

    with pytest.raises(RuntimeError, match="exceeded 10 rounds"):
        agent._call_llm_with_tools("q")
