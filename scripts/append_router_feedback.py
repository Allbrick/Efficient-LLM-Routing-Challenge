from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


FIELDNAMES = [
    "timestamp",
    "prompt",
    "budget_tier",
    "selected_model_id",
    "selection_reason",
    "action_type",
    "was_wrong",
    "expected_model_id",
    "user_note",
    "history_model_id",
    "history_output",
    "evaluator_score",
    "evaluator_sufficient",
    "escalated_to",
    "final_selected_model_id",
]


@dataclass(frozen=True)
class RouterFeedback:
    timestamp: str
    prompt: str
    budget_tier: str
    selected_model_id: str
    selection_reason: str
    action_type: str
    was_wrong: str
    expected_model_id: str
    user_note: str
    history_model_id: str = ""
    history_output: str = ""
    evaluator_score: str = ""
    evaluator_sufficient: str = ""
    escalated_to: str = ""
    final_selected_model_id: str = ""


def append_feedback(output: str | Path, feedback: RouterFeedback) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(asdict(feedback))
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Append a misrouting or routing-quality feedback row.")
    parser.add_argument("--output", default="data/router_feedback/online_feedback.csv")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--budget_tier", required=True, choices=["fast", "balanced", "premium"])
    parser.add_argument("--selected", required=True, choices=["cheap", "mid", "premium", "abstain"])
    parser.add_argument("--expected", default="")
    parser.add_argument("--selection_reason", default="")
    parser.add_argument("--action_type", default="call_model")
    parser.add_argument("--was_wrong", default="true", choices=["true", "false"])
    parser.add_argument("--note", default="")
    parser.add_argument("--history_model_id", default="")
    parser.add_argument("--history_output", default="")
    parser.add_argument("--evaluator_score", default="")
    parser.add_argument("--evaluator_sufficient", default="")
    parser.add_argument("--escalated_to", default="")
    parser.add_argument("--final_selected_model_id", default="")
    args = parser.parse_args()

    feedback = RouterFeedback(
        timestamp=datetime.now(timezone.utc).isoformat(),
        prompt=args.prompt,
        budget_tier=args.budget_tier,
        selected_model_id=args.selected,
        selection_reason=args.selection_reason,
        action_type=args.action_type,
        was_wrong=args.was_wrong,
        expected_model_id=args.expected,
        user_note=args.note,
        history_model_id=args.history_model_id,
        history_output=args.history_output,
        evaluator_score=args.evaluator_score,
        evaluator_sufficient=args.evaluator_sufficient,
        escalated_to=args.escalated_to,
        final_selected_model_id=args.final_selected_model_id,
    )
    path = append_feedback(args.output, feedback)
    print(f"appended feedback: {path}")


if __name__ == "__main__":
    main()
