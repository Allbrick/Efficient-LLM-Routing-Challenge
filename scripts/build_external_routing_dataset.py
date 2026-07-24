from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from routing_stack.training.external_dataset import read_routing_csv


SPEC_COLUMNS = (
    "prompt_id",
    "prompt",
    "task_type",
    "difficulty",
    "risk_level",
    "expected_min_model",
    "evaluation_type",
    "reference_answer",
    "test_spec",
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build eval-spec compatible rows from filtered external routing prompts."
    )
    parser.add_argument("--input", default="data/external/routing_prompts.csv")
    parser.add_argument("--output", default="data/external/external_eval_specs.csv")
    parser.add_argument("--summary", default="data/external/external_dataset_summary.json")
    args = parser.parse_args()

    rows = read_routing_csv(args.input)
    specs = build_external_eval_specs(rows)
    write_specs(args.output, specs)
    summary = summarize_external_rows(rows, specs)
    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def build_external_eval_specs(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    specs = []
    seen = set()
    for row in rows:
        prompt_id = str(row.get("prompt_id", "")).strip()
        if not prompt_id or prompt_id in seen:
            continue
        seen.add(prompt_id)
        specs.append(
            {
                "prompt_id": prompt_id,
                "prompt": str(row.get("prompt", "")).strip(),
                "task_type": str(row.get("task_type", "") or "external_instruction").strip(),
                "difficulty": str(row.get("difficulty", "") or "unknown").strip(),
                "risk_level": str(row.get("risk_level", "") or "unknown").strip(),
                "expected_min_model": str(row.get("expected_min_model", "") or "mid").strip(),
                "evaluation_type": str(row.get("evaluation_type", "") or "rubric_check").strip(),
                "reference_answer": "",
                "test_spec": build_test_spec(row),
            }
        )
    return specs


def build_test_spec(row: dict[str, str]) -> str:
    payload = {
        "source": row.get("source", ""),
        "license": row.get("license", ""),
        "source_url": row.get("source_url", ""),
        "label_confidence": row.get("label_confidence", "0.5"),
        "note": "external weak label; review or evaluator validation recommended before final training",
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def summarize_external_rows(rows: list[dict[str, str]], specs: list[dict[str, str]]) -> dict:
    return {
        "input_rows": len(rows),
        "spec_rows": len(specs),
        "source_counts": count_by(rows, "source"),
        "license_counts": count_by(rows, "license"),
        "expected_min_model_counts": count_by(specs, "expected_min_model"),
        "difficulty_counts": count_by(specs, "difficulty"),
        "risk_level_counts": count_by(specs, "risk_level"),
        "evaluation_type_counts": count_by(specs, "evaluation_type"),
    }


def count_by(rows: list[dict[str, str]], key: str) -> dict[str, int]:
    counts = {}
    for row in rows:
        value = str(row.get(key, "") or "").strip() or "<empty>"
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def write_specs(path: str | Path, specs: list[dict[str, str]]) -> None:
    import csv

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(SPEC_COLUMNS))
        writer.writeheader()
        writer.writerows(specs)


if __name__ == "__main__":
    main()
