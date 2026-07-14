from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from geometric_router.router import GeometricRouter
from geometric_router.tuning import tune_router_policy


def main() -> None:
    parser = argparse.ArgumentParser(description="Tune geometric router radius policy by simulation.")
    parser.add_argument("--artifact", default="artifacts/geometric_router.json")
    parser.add_argument("--train_path", default="data/public/example_train.csv")
    parser.add_argument("--specs_path", default="data/public/example_eval_specs.csv")
    parser.add_argument("--output", default="artifacts/geometric_router.json")
    args = parser.parse_args()

    router = GeometricRouter.load(args.artifact)
    train_df = pd.read_csv(args.train_path)
    specs_df = pd.read_csv(args.specs_path) if Path(args.specs_path).exists() else pd.DataFrame()
    results = tune_router_policy(router, train_df, specs_df)
    router.save(args.output)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
