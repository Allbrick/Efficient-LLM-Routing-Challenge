from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from routing_stack.training.outcome_matrix import build_outcome_matrix_from_training


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an outcome-matrix CSV from existing model outputs.")
    parser.add_argument("--train_path", default="data/public/example_train.csv")
    parser.add_argument("--specs_path", default="data/public/example_eval_specs.csv")
    parser.add_argument("--output", default="data/router_outcomes/public_outcome_matrix.csv")
    parser.add_argument("--fallback_threshold", type=float, default=0.85)
    args = parser.parse_args()

    train_df = pd.read_csv(args.train_path)
    specs_df = pd.read_csv(args.specs_path)
    matrix = build_outcome_matrix_from_training(
        train_df,
        specs_df,
        fallback_threshold=args.fallback_threshold,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    matrix.to_csv(output, index=False, encoding="utf-8")
    summary = {
        "output": str(output),
        "prompt_rows": int(len(matrix)),
        "columns": list(matrix.columns),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
