# tests/test_llm.py
import os

from dotenv import load_dotenv

load_dotenv()


def test_litellm_smoke(llm_completion):
    """LiteLLM smoke test. Falls back to a mock if the real model fails."""
    model = os.getenv("LITELLM_MODEL")  # e.g. claude-haiku-4-5-20251001

    response = llm_completion(
        model=model,
        messages=[{"role": "user", "content": "Say hello!"}],
    )

    content = response.choices[0].message.content
    assert isinstance(content, str)
    assert content.strip()
    print(content)
