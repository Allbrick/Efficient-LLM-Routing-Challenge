from __future__ import annotations

from pathlib import Path

import pandas as pd

from router_impls.geometric.router import GeometricRouter
from routing_stack.training.calibration_reports import (
    build_ood_calibration,
    build_sufficiency_calibration,
)


DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "public"


def test_build_sufficiency_calibration_reports_model_bins():
    train_df = pd.read_csv(DATA_DIR / "example_train.csv")
    specs_df = pd.read_csv(DATA_DIR / "example_eval_specs.csv")
    router = GeometricRouter.fit(train_df, specs_df)

    calibration_df, summary_df = build_sufficiency_calibration(router, train_df, specs_df, bins=5)

    assert {"model_id", "bin", "actual_success_rate", "calibration_gap"} <= set(calibration_df.columns)
    assert set(summary_df["model_id"]) == {"cheap", "mid", "premium"}
    assert "ece" in summary_df.columns


def test_build_ood_calibration_reports_ood_bins():
    train_df = pd.read_csv(DATA_DIR / "example_train.csv")
    specs_df = pd.read_csv(DATA_DIR / "example_eval_specs.csv")
    router = GeometricRouter.fit(train_df, specs_df)

    calibration_df, summary = build_ood_calibration(router, train_df, specs_df, bins=5)

    assert {"ood_bin", "cheap_success_rate", "under_route_rate"} <= set(calibration_df.columns)
    assert summary["count"] == train_df["prompt_id"].nunique()
    assert "ood_low_cheap_success_rate" in summary
