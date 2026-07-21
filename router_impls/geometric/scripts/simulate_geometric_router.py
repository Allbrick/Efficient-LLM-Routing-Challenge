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

from router_impls.geometric.router import GeometricRouter
from router_impls.geometric.simulator import simulate_public_set
from router_impls.geometric.budget_allocator import allocate_public_budget


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate geometric router on the public sample set.")
    parser.add_argument("--artifact", default="artifacts/geometric_router.json")
    parser.add_argument("--train_path", default="data/public/example_train.csv")
    parser.add_argument("--specs_path", default="data/public/example_eval_specs.csv")
    parser.add_argument("--output", default="artifacts/geometric_simulation.json")
    parser.add_argument("--allocate", action="store_true")
    parser.add_argument("--tier", default="fast", choices=["fast", "balanced", "premium"])
    args = parser.parse_args()

    router = GeometricRouter.load(args.artifact)
    train_df = pd.read_csv(args.train_path)
    specs_df = pd.read_csv(args.specs_path) if Path(args.specs_path).exists() else pd.DataFrame()
    if args.allocate:
        payload = allocate_public_budget(router, train_df, specs_df, args.tier)
        printable = payload["summary"]
    else:
        payload = simulate_public_set(router, train_df, specs_df)
        printable = payload["summary"]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(printable, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


