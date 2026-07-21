from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from router_impls.geometric.budget_allocator import allocate_public_budget
from router_impls.geometric.router import GeometricRouter


def main() -> None:
    parser = argparse.ArgumentParser(description="Run batch budget allocation for the geometric router.")
    parser.add_argument("--artifact", default="artifacts/geometric_router.json")
    parser.add_argument("--train_path", default="data/public/example_train.csv")
    parser.add_argument("--specs_path", default="data/public/example_eval_specs.csv")
    parser.add_argument("--tier", default="fast", choices=["fast", "balanced", "premium"])
    parser.add_argument("--output", default="artifacts/geometric_allocation.json")
    args = parser.parse_args()

    router = GeometricRouter.load(args.artifact)
    train_df = pd.read_csv(args.train_path)
    specs_df = pd.read_csv(args.specs_path) if Path(args.specs_path).exists() else pd.DataFrame()
    payload = allocate_public_budget(router, train_df, specs_df, args.tier)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


