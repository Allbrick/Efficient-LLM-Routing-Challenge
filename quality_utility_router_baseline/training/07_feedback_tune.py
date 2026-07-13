"""Evaluate router feedback cases and report routing errors.

This script does not mutate model artifacts. It is the first layer of the
feedback loop:

    user correction -> router_feedback.csv -> this evaluator -> regression test

Future tuning can use this report to update training rows or learn a small
policy calibration model.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.serve_router_viewer import RouterService


MODEL_RANK = {"cheap": 0, "mid": 1, "premium": 2}


@dataclass
class FeedbackResult:
    case_id: str
    prompt: str
    budget_tier: str
    expected_model: str
    predicted_model: str
    error_type: str
    prompt_complexity: float
    reason: str


def classify_error(expected: str, predicted: str) -> str:
    if expected == predicted:
        return "ok"
    if MODEL_RANK[predicted] < MODEL_RANK[expected]:
        return "under_route"
    return "over_route"


def evaluate_feedback(feedback_path: Path, artifacts_dir: Path) -> list[FeedbackResult]:
    feedback = pd.read_csv(feedback_path).fillna("")
    service = RouterService(artifacts_dir)
    results: list[FeedbackResult] = []

    for row in feedback.itertuples(index=False):
        route = service.route(row.prompt, row.budget_tier)
        predicted = route["selected_model_id"]
        expected = row.expected_model
        results.append(
            FeedbackResult(
                case_id=row.case_id,
                prompt=row.prompt,
                budget_tier=row.budget_tier,
                expected_model=expected,
                predicted_model=predicted,
                error_type=classify_error(expected, predicted),
                prompt_complexity=float(route["prompt_complexity"]),
                reason=row.reason,
            )
        )

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate router feedback cases.")
    parser.add_argument("--feedback_path", default="../data/public/router_feedback.csv")
    parser.add_argument("--artifacts_dir", default="artifacts")
    parser.add_argument("--output", default="artifacts/feedback_report.json")
    parser.add_argument("--fail_on_error", action="store_true")
    args = parser.parse_args()

    results = evaluate_feedback(Path(args.feedback_path), Path(args.artifacts_dir))
    errors = [result for result in results if result.error_type != "ok"]
    summary = {
        "total": len(results),
        "passed": len(results) - len(errors),
        "failed": len(errors),
        "under_route": sum(result.error_type == "under_route" for result in errors),
        "over_route": sum(result.error_type == "over_route" for result in errors),
    }

    output_payload = {
        "summary": summary,
        "results": [asdict(result) for result in results],
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if errors:
        print("\nFailed cases:")
        for result in errors:
            print(
                f"  {result.case_id}: expected={result.expected_model} "
                f"predicted={result.predicted_model} tier={result.budget_tier} "
                f"type={result.error_type}"
            )

    if args.fail_on_error and errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
