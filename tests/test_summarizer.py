# tests/test_summarizer.py
import pytest

from src.agents.summarizer_agent import SummarizerAgent

FILTERED = """# Filtered AI/ML Articles

**Total Input:** 4
**Total Output:** 2

---

## GPT-4 Released by OpenAI

**URL:** https://example.com/gpt4
**Relevance Score:** 10/10
**Reasoning:** Major LLM release
**Key Topics:** LLM, GPT

OpenAI announces GPT-4.

---

## New Vision Transformer Beats Benchmarks

**URL:** https://example.com/vit
**Relevance Score:** 8/10
**Reasoning:** Computer vision research result
**Key Topics:** Vision, Transformers

A new vision model.

---
"""


@pytest.mark.asyncio
async def test_summarizer_groups_by_topic(llm_completion, tmp_path):
    """Summarize filtered articles by topic (real LLM, mock fallback if it fails)."""
    input_file = tmp_path / "filtered_articles.md"
    output_file = tmp_path / "summary.md"
    input_file.write_text(FILTERED, encoding="utf-8")

    agent = SummarizerAgent()
    result = await agent.execute(str(input_file), str(output_file))

    assert result["success"] is True
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")

    # Structure comes from the agent, so it holds for real and mock LLM output
    assert "AI/ML Daily Digest" in content
    assert "**Total Articles:** 2" in content
    assert "## LLM (1 articles)" in content
    assert "## Vision (1 articles)" in content
