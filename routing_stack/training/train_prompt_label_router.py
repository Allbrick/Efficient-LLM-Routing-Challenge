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

from routing_stack.training.prompt_label_model import PromptLabelRouterModel
from routing_stack.training.prompt_label_csv import read_prompt_label_csv_file


def train_from_csv(csv_path: str | Path, output_path: str | Path) -> dict:
    prompts, labels = _read_rows(csv_path)
    model = PromptLabelRouterModel().fit(prompts, labels)
    model.save(output_path)
    label_counts = {label: labels.count(label) for label in sorted(set(labels))}
    return {
        "csv_path": str(csv_path),
        "output_path": str(output_path),
        "row_count": len(prompts),
        "label_counts": label_counts,
    }


def _read_rows(csv_path: str | Path) -> tuple[list[str], list[str]]:
    rows = read_prompt_label_csv_file(csv_path)
    prompts = [row["prompt"] for row in rows]
    labels = [row["label"] for row in rows]
    if not prompts:
        raise ValueError("학습 가능한 row가 없습니다.")
    return prompts, labels


def main() -> None:
    parser = argparse.ArgumentParser(description="Prompt/정답 CSV로 learned_label 라우터 artifact를 학습합니다.")
    parser.add_argument("--csv", default="data/router_labels/prompt_labels.csv")
    parser.add_argument("--output", default="artifacts/prompt_label_router.joblib")
    args = parser.parse_args()

    payload = train_from_csv(args.csv, args.output)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
