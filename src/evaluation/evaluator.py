"""Evaluation framework for news filtering agent."""

import json
from pathlib import Path
from typing import Dict, List
from src.agents.news_filter_agent import NewsFilterAgent
import asyncio


class FilterEvaluator:
    """
    Evaluates news filtering agent.

    Measures:
    - Accuracy (correct classification)
    - Precision (% of relevant that are actually relevant)
    - Recall (% of actual relevant found)

    Test cases the agent could not judge (API quota, network, invalid
    response) are excluded from the metrics and reported as errors, so an
    outage can never be mistaken for a bad prediction.
    """

    def __init__(self, golden_dataset_path: str):
        self.golden_dataset_path = Path(golden_dataset_path)
        self.agent = NewsFilterAgent()
        self.relevance_threshold = 6

    async def evaluate(self) -> Dict:
        """Run evaluation on golden dataset."""
        # Load golden dataset
        with open(self.golden_dataset_path, encoding="utf-8") as f:
            dataset = json.load(f)

        test_cases = dataset["test_cases"]
        print(f"📊 Evaluating on {len(test_cases)} test cases...")

        results = []

        for test_case in test_cases:
            print(
                f"   [{test_case['id']}/{len(test_cases)}] {test_case['title'][:50]}..."
            )

            # Run agent
            judgment = self.agent._judge_relevance(
                {"title": test_case["title"], "summary": test_case["summary"]}
            )
            expected_relevant = test_case["expected_relevant"]

            # The agent could not judge this case: record it, but keep it out
            # of the metrics.
            if judgment.get("error"):
                results.append(
                    {
                        "test_case_id": test_case["id"],
                        "title": test_case["title"],
                        "expected": expected_relevant,
                        "predicted": None,
                        "correct": None,
                        "score": 0,
                        "reasoning": judgment["reasoning"],
                        "error": True,
                    }
                )
                print("      ⚠️  Could not judge (API/parse error), excluded")
                continue

            # Check prediction
            predicted_relevant = (
                judgment["relevant"]
                and judgment["relevance_score"] >= self.relevance_threshold
            )

            correct = predicted_relevant == expected_relevant

            results.append(
                {
                    "test_case_id": test_case["id"],
                    "title": test_case["title"],
                    "expected": expected_relevant,
                    "predicted": predicted_relevant,
                    "correct": correct,
                    "score": judgment["relevance_score"],
                    "reasoning": judgment["reasoning"],
                    "error": False,
                }
            )

            status = "✅" if correct else "❌"
            print(
                f"      {status} Expected: {expected_relevant}, Predicted: {predicted_relevant}"
            )

        valid = [r for r in results if not r["error"]]
        errors = len(results) - len(valid)

        if not valid:
            raise RuntimeError(
                f"Evaluation invalid: all {len(results)} test cases failed "
                "(API/parse errors). Check quota, API key and model."
            )

        # Calculate metrics only over the cases that were really judged
        metrics = self._calculate_metrics(valid)
        metrics["errors"] = errors

        return {
            "results": results,
            "metrics": metrics,
            "test_cases": len(test_cases),
        }

    def _calculate_metrics(self, results: List[Dict]) -> Dict:
        """Calculate evaluation metrics."""
        # Accuracy
        correct = sum(1 for r in results if r["correct"])
        accuracy = correct / len(results)

        # Precision, Recall, F1
        true_positives = sum(1 for r in results if r["expected"] and r["predicted"])
        false_positives = sum(
            1 for r in results if not r["expected"] and r["predicted"]
        )
        false_negatives = sum(
            1 for r in results if r["expected"] and not r["predicted"]
        )

        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0
        )

        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0
        )

        f1 = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0
        )

        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "correct": correct,
            "total": len(results),
        }

    async def save_report(self, evaluation: Dict, output_path: str):
        """Save evaluation report."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# News Filter Agent - Evaluation Report\n\n")

            # Metrics
            metrics = evaluation["metrics"]
            errors = metrics.get("errors", 0)
            if errors:
                f.write(
                    f"> ⚠️ **INCOMPLETE:** {errors} of {evaluation['test_cases']} "
                    "test cases could not be judged (API/parse errors) and were "
                    "excluded from the metrics.\n\n"
                )
            f.write("## Overall Metrics\n\n")
            f.write(f"- **Accuracy:** {metrics['accuracy']:.1%}\n")
            f.write(f"- **Precision:** {metrics['precision']:.1%}\n")
            f.write(f"- **Recall:** {metrics['recall']:.1%}\n")
            f.write(f"- **F1 Score:** {metrics['f1_score']:.3f}\n")
            f.write(
                f"- **Test Cases:** {metrics['correct']}/{metrics['total']} correct\n\n"
            )

            # Results
            f.write("## Test Results\n\n")

            for result in evaluation["results"]:
                if result["error"]:
                    status = "⚠️ ERROR"
                else:
                    status = "✅ PASS" if result["correct"] else "❌ FAIL"
                f.write(f"### [{result['test_case_id']}] {status}\n\n")
                f.write(f"**Title:** {result['title']}\n\n")
                f.write(
                    f"- Expected: {'Relevant' if result['expected'] else 'Not Relevant'}\n"
                )
                if result["error"]:
                    f.write("- Predicted: n/a (could not judge)\n")
                else:
                    f.write(
                        f"- Predicted: {'Relevant' if result['predicted'] else 'Not Relevant'} (score: {result['score']})\n"
                    )
                f.write(f"- Reasoning: {result['reasoning']}\n\n")
                f.write("---\n\n")

        print(f"💾 Evaluation report saved to {output_path}")


# Run evaluation
async def run_evaluation():
    """Run evaluation and save report."""
    print("=" * 60)
    print("  News Filter Agent Evaluation")
    print("=" * 60)

    evaluator = FilterEvaluator("data/evaluation/golden_dataset.json")
    evaluation = await evaluator.evaluate()

    print("\n📊 Results:")
    print(f"   Accuracy:  {evaluation['metrics']['accuracy']:.1%}")
    print(f"   Precision: {evaluation['metrics']['precision']:.1%}")
    print(f"   Recall:    {evaluation['metrics']['recall']:.1%}")
    print(f"   F1 Score:  {evaluation['metrics']['f1_score']:.3f}")
    if evaluation["metrics"]["errors"]:
        print(
            f"   ⚠️  INCOMPLETE: {evaluation['metrics']['errors']} test cases "
            "could not be judged and were excluded"
        )

    await evaluator.save_report(evaluation, "data/evaluation/evaluation_report.md")

    print("\n✅ Evaluation complete!")
    print("   Report: data/evaluation/evaluation_report.md")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
