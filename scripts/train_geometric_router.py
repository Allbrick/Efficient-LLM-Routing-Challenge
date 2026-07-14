from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from geometric_router.evaluator import build_training_labels
from geometric_router.router import GeometricRouter


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the geometric LLM router MVP.")
    parser.add_argument("--train_path", default="data/public/example_train.csv")
    parser.add_argument("--specs_path", default="data/public/example_eval_specs.csv")
    parser.add_argument("--output", default="artifacts/geometric_router.json")
    parser.add_argument("--labels_output", default="artifacts/geometric_labels.csv")
    parser.add_argument("--fallback_threshold", type=float, default=0.85)
    parser.add_argument("--radius_quantile", type=float, default=0.90)
    args = parser.parse_args()

    train_df = pd.read_csv(args.train_path)
    specs_df = pd.read_csv(args.specs_path) if Path(args.specs_path).exists() else pd.DataFrame()

    router = GeometricRouter.fit(
        train_df,
        specs_df,
        fallback_threshold=args.fallback_threshold,
        radius_quantile=args.radius_quantile,
    )
    router.save(args.output)

    labels = build_training_labels(train_df, specs_df, fallback_threshold=args.fallback_threshold)
    labels_path = Path(args.labels_output)
    labels_path.parent.mkdir(parents=True, exist_ok=True)
    labels.to_csv(labels_path, index=False)

    summary = {
        "artifact": args.output,
        "labels": args.labels_output,
        "metadata": router.metadata,
        "envelopes": {
            model: {
                "sample_count": envelope.sample_count,
                "radius": envelope.radius,
            }
            for model, envelope in router.envelopes.items()
        },
        "frontier": router.frontier,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
