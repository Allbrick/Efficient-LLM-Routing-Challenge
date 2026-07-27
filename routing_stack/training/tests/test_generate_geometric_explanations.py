from __future__ import annotations

from pathlib import Path

import pandas as pd

from router_impls.geometric.router import GeometricRouter
from scripts.generate_geometric_explanations import generate_geometric_explanations


DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "public"


def test_generate_geometric_explanations_includes_ood_and_lane_columns(tmp_path):
    demo_df = pd.DataFrame(
        [
            {
                "demo_case": "easy",
                "prompt_id": "demo_1",
                "prompt": "안녕",
                "task_type": "",
                "difficulty": "",
                "risk_level": "",
                "evaluation_type": "",
                "expected_min_model": "cheap",
            }
        ]
    )

    train_df = pd.read_csv(DATA_DIR / "example_train.csv")
    specs_df = pd.read_csv(DATA_DIR / "example_eval_specs.csv")
    router = GeometricRouter.fit(train_df, specs_df)

    generate_geometric_explanations(router, demo_df, tmp_path)

    detail_df = pd.read_csv(tmp_path / "geometric_explanations.csv")
    summary_df = pd.read_csv(tmp_path / "geometric_explanations_summary.csv")

    for column in ("pre_route_lane", "pre_route_reason", "ood_score", "uncertainty_score", "ood_high"):
        assert column in detail_df.columns
        assert column in summary_df.columns
