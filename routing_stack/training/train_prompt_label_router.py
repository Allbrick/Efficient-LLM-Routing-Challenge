from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from routing_stack.training.prompt_label_csv import read_prompt_label_csv_file
from routing_stack.training.prompt_label_model import PromptLabelRouterModel


def train_from_csv(csv_path: str | Path, output_path: str | Path) -> dict:
    prompts, routing_scores = _read_rows(csv_path)
    model = PromptLabelRouterModel().fit(prompts, routing_scores)
    model.save(output_path)
    bucket_counts = {
        "cheap": sum(1 for score in routing_scores if score <= 40),
        "mid": sum(1 for score in routing_scores if 40 < score <= 70),
        "premium": sum(1 for score in routing_scores if score > 70),
    }
    return {
        "csv_path": str(csv_path),
        "output_path": str(output_path),
        "row_count": len(prompts),
        "score_min": min(routing_scores),
        "score_max": max(routing_scores),
        "score_mean": round(sum(routing_scores) / len(routing_scores), 3),
        "bucket_counts": bucket_counts,
    }


def _read_rows(csv_path: str | Path) -> tuple[list[str], list[float]]:
    rows = read_prompt_label_csv_file(csv_path)
    prompts = [str(row["prompt"]) for row in rows]
    routing_scores = [float(row["routing_score"]) for row in rows]
    if not prompts:
        raise ValueError("No trainable rows found.")
    return prompts, routing_scores


def main() -> None:
    parser = argparse.ArgumentParser(description="Train learned_label router artifact from prompt,routing_score CSV.")
    parser.add_argument("--csv", default="data/router_labels/prompt_labels.csv")
    parser.add_argument("--output", default="artifacts/prompt_label_router.joblib")
    args = parser.parse_args()

    payload = train_from_csv(args.csv, args.output)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
