from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from router_impls.geometric.router import GeometricRouter
from routing_stack.training.calibration_reports import build_ood_calibration
from routing_stack.training.outcome_matrix import merge_outcome_training


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate geometric OOD calibration report assets.")
    parser.add_argument("--artifact", default="artifacts/geometric_router.json")
    parser.add_argument("--train_path", default="data/public/example_train.csv")
    parser.add_argument("--specs_path", default="data/public/example_eval_specs.csv")
    parser.add_argument("--outcome_matrix_path", default="")
    parser.add_argument("--output_dir", default="docs/report_assets")
    parser.add_argument("--bins", type=int, default=10)
    args = parser.parse_args()

    router = GeometricRouter.load(args.artifact)
    train_df = pd.read_csv(args.train_path)
    specs_df = pd.read_csv(args.specs_path)
    if args.outcome_matrix_path:
        train_df, specs_df, _summary = merge_outcome_training(train_df, specs_df, args.outcome_matrix_path)
    calibration_df, summary = build_ood_calibration(
        router,
        train_df,
        specs_df,
        bins=args.bins,
    )

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    calibration_df.to_csv(output / "ood_calibration.csv", index=False, encoding="utf-8")
    payload = {
        "files": [
            "ood_calibration.csv",
            "ood_calibration_summary.json",
        ],
        "summary": summary,
    }
    (output / "ood_calibration_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
