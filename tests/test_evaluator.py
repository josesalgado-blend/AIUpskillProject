# tests/test_evaluator.py
"""Evaluator tests with a fake judge: no network, no API quota."""

import json

import pytest

from src.evaluation.evaluator import FilterEvaluator

CASES = [
    {"id": 1, "title": "GPT-4 Released", "summary": "s", "expected_relevant": True},
    {"id": 2, "title": "New JS Framework", "summary": "s", "expected_relevant": False},
    {"id": 3, "title": "ML in Healthcare", "summary": "s", "expected_relevant": True},
    {"id": 4, "title": "Docker 25", "summary": "s", "expected_relevant": False},
]


def _make_evaluator(tmp_path, monkeypatch, judge):
    """Build an evaluator over CASES whose agent uses the fake `judge`."""
    monkeypatch.setenv("LITELLM_MODEL", "mock/model")
    dataset = tmp_path / "golden.json"
    dataset.write_text(json.dumps({"test_cases": CASES}), encoding="utf-8")
    evaluator = FilterEvaluator(str(dataset))
    evaluator.agent._judge_relevance = judge
    return evaluator


def _ok(relevant, score):
    return {
        "relevant": relevant,
        "relevance_score": score,
        "reasoning": "fake",
        "key_topics": [],
    }


@pytest.mark.asyncio
async def test_metrics_for_known_predictions(tmp_path, monkeypatch):
    """1 false negative: 3 of 4 correct, precision 100%, recall 50%."""
    answers = {
        "GPT-4 Released": _ok(True, 10),  # TP
        "New JS Framework": _ok(False, 1),  # TN
        "ML in Healthcare": _ok(False, 2),  # FN
        "Docker 25": _ok(False, 1),  # TN
    }
    evaluator = _make_evaluator(
        tmp_path, monkeypatch, lambda article: answers[article["title"]]
    )

    evaluation = await evaluator.evaluate()
    metrics = evaluation["metrics"]

    assert metrics["accuracy"] == pytest.approx(0.75)
    assert metrics["precision"] == pytest.approx(1.0)
    assert metrics["recall"] == pytest.approx(0.5)
    assert metrics["f1_score"] == pytest.approx(2 / 3)
    assert metrics["errors"] == 0


@pytest.mark.asyncio
async def test_api_errors_are_excluded_not_counted_as_wrong(tmp_path, monkeypatch):
    """A failed call must not become a 'not relevant' prediction."""

    def judge(article):
        if article["title"] == "ML in Healthcare":
            return {
                "relevant": False,
                "relevance_score": 0,
                "reasoning": "Failed to judge: 429",
                "key_topics": [],
                "error": True,
            }
        return _ok(article["title"] == "GPT-4 Released", 10)

    evaluator = _make_evaluator(tmp_path, monkeypatch, judge)
    evaluation = await evaluator.evaluate()
    metrics = evaluation["metrics"]

    assert metrics["errors"] == 1
    assert metrics["total"] == 3  # the errored case is not in the metrics
    assert metrics["accuracy"] == pytest.approx(1.0)
    assert len(evaluation["results"]) == 4  # but it is still reported


@pytest.mark.asyncio
async def test_all_errors_raise(tmp_path, monkeypatch):
    """If nothing could be judged the evaluation is invalid, not 0%."""
    evaluator = _make_evaluator(
        tmp_path,
        monkeypatch,
        lambda article: {
            "relevant": False,
            "relevance_score": 0,
            "reasoning": "Failed to judge: 429",
            "key_topics": [],
            "error": True,
        },
    )

    with pytest.raises(RuntimeError, match="Evaluation invalid"):
        await evaluator.evaluate()


@pytest.mark.asyncio
async def test_report_is_utf8_and_flags_incomplete(tmp_path, monkeypatch):
    """The report is written in UTF-8 and warns when results are incomplete."""

    def judge(article):
        if article["title"] == "Docker 25":
            return {
                "relevant": False,
                "relevance_score": 0,
                "reasoning": "Failed to judge: límite",
                "key_topics": [],
                "error": True,
            }
        return _ok(article["title"] != "New JS Framework", 9)

    evaluator = _make_evaluator(tmp_path, monkeypatch, judge)
    evaluation = await evaluator.evaluate()
    report = tmp_path / "report.md"
    await evaluator.save_report(evaluation, str(report))

    text = report.read_text(encoding="utf-8")
    assert "INCOMPLETE" in text
    assert "⚠️ ERROR" in text
    assert "límite" in text
