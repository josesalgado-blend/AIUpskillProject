"""Shared pytest fixtures.

This file is automatically loaded by pytest. Add fixtures here as you build
out test coverage milestone by milestone (e.g. a `tmp_articles_dir` fixture
in M1, an `llm_response` fixture in M3, a `mcp_client` fixture in M4).
"""

from __future__ import annotations

import os
import re
from types import SimpleNamespace

import litellm
import pytest

# --- LLM with mock fallback ------------------------------------------------
# Tests try the real model configured in LITELLM_MODEL first. If it fails
# (quota, 503, missing key...), they fall back to canned responses so the
# suite never depends on the provider. After the first failure the real model
# is not retried in the same session.

_llm_state = {"real_ok": True}

_AI_KEYWORDS = ("gpt", "llm", "machine learning", "neural", "openai", "ai ")


def _fake_response(messages: list[dict]) -> SimpleNamespace:
    """Build a LiteLLM-shaped response with deterministic content."""
    prompt = messages[-1]["content"] if messages else ""
    title_match = re.search(r"Title: (.+)", prompt)

    if title_match and "relevance_score" in prompt:
        title = title_match.group(1).lower()
        relevant = any(word in title for word in _AI_KEYWORDS)
        content = (
            '{"relevant": %s, "relevance_score": %d, '
            '"reasoning": "mock judgment", "key_topics": []}'
        ) % ("true" if relevant else "false", 9 if relevant else 1)
    elif "Summarize these" in prompt:
        # SummarizerAgent: lines look like "- <title>: <reasoning>"
        titles = re.findall(r"^- (.+?):", prompt, flags=re.MULTILINE)
        content = f"Mock summary covering {len(titles)} article(s): " + "; ".join(
            titles
        )
    elif "daily AI/ML newsletter" in prompt:
        # WriterAgent: echo the summary so the newsletter keeps its content
        summary = prompt.split("Here's the summary of today's articles:")[-1]
        summary = summary.split("Write an engaging newsletter")[0].strip()
        content = f"Hello readers! (mock newsletter)\n\n{summary}\n\nSee you tomorrow."
    else:
        content = "Hello! (mock response)"

    message = SimpleNamespace(
        content=content,
        tool_calls=None,
        model_dump=lambda: {"role": "assistant", "content": content},
    )
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def completion_with_fallback(**kwargs):
    """Call the real LiteLLM model; on any failure, return a mock response."""
    if _llm_state["real_ok"]:
        try:
            return litellm.completion(**kwargs)
        except Exception as e:
            _llm_state["real_ok"] = False
            print(f"\n⚠️  Real LLM unavailable ({type(e).__name__}); using mocks")
    return _fake_response(kwargs.get("messages", []))


@pytest.fixture
def llm_completion(monkeypatch):
    """Make agents use the real LLM, falling back to mocks if it fails."""
    monkeypatch.setattr("src.agents.base_agent.completion", completion_with_fallback)
    # Agents require a model name; use a placeholder when none is configured
    # (the real call then fails and the mock fallback takes over).
    if not os.getenv("LITELLM_MODEL"):
        monkeypatch.setenv("LITELLM_MODEL", "mock/model")
    return completion_with_fallback


@pytest.fixture
def sample_article_kwargs() -> dict:
    """Minimal kwargs for constructing an Article in tests.

    You'll define the Article dataclass in Milestone 1. Once it exists,
    tests can use this fixture to build instances without repeating boilerplate.
    """
    from datetime import datetime

    return {
        "title": "Sample article for tests",
        "url": "https://example.com/sample",
        "published_at": datetime(2026, 1, 1, 12, 0, 0),
        "source": "test",
    }
