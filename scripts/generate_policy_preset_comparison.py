from __future__ import annotations

import argparse
import json
import os
import sys
from copy import deepcopy
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from router_impls.geometric.policy_presets import POLICY_PRESETS, apply_policy_preset
from router_impls.geometric.router import GeometricRouter
from router_impls.geometric.simulator import simulate_public_set


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare tier-specific geometric policy presets.")
    parser.add_argument("--router_path", default="artifacts/geometric_router.json")
    parser.add_argument("--train_path", default="data/public/example_train.csv")
    parser.add_argument("--specs_path", default="data/public/example_eval_specs.csv")
    parser.add_argument("--output_dir", default="docs/report_assets")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    train_df = pd.read_csv(args.train_path)
    specs_df = pd.read_csv(args.specs_path)
    base_router = GeometricRouter.load(args.router_path)

    rows = []
    for preset_name in POLICY_PRESETS:
        router = apply_policy_preset(deepcopy(base_router), preset_name)
        summary = simulate_public_set(router, train_df, specs_df)["summary"]["tier_summary"]
        for tier, item in summary.items():
            rows.append({"preset": preset_name, "tier": tier, **item})

    comparison = pd.DataFrame(rows)
    comparison_path = output_dir / "policy_preset_comparison.csv"
    summary_path = output_dir / "policy_preset_comparison_summary.json"
    comparison.to_csv(comparison_path, index=False)
    summary = {
        "files": [comparison_path.name],
        "presets": sorted(POLICY_PRESETS),
        "rows": comparison.to_dict(orient="records"),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output_dir": str(output_dir), **summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
