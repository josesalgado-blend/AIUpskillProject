# Test base agent
import pytest

from src.agents.base_agent import BaseAgent


class EchoAgent(BaseAgent):
    """Minimal concrete agent (not named Test* so pytest doesn't collect it)."""

    async def _load_context(self, input_path):
        return {"test": "data"}

    async def _process(self, context):
        response = self._call_llm("Say hello")
        return {"response": response}

    async def _save_result(self, result, output_path):
        self.saved = result


@pytest.mark.asyncio
async def test_base_agent_template_method(llm_completion):
    """execute() runs load -> process -> save. Falls back to mock LLM on failure."""
    agent = EchoAgent()

    result = await agent.execute("input.md", "output.md")

    assert result["success"] is True
    assert result["input_path"] == "input.md"
    assert result["output_path"] == "output.md"
    assert agent.saved["response"].strip()
