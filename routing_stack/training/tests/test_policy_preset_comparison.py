from __future__ import annotations

import pandas as pd

from router_impls.geometric.policy_presets import POLICY_PRESETS, apply_policy_preset
from router_impls.geometric.router import GeometricRouter


def test_policy_presets_apply_to_router():
    train_df = pd.read_csv("data/public/example_train.csv")
    specs_df = pd.read_csv("data/public/example_eval_specs.csv")
    router = GeometricRouter.fit(train_df.head(12), specs_df.head(4), include_synthetic=False)

    apply_policy_preset(router, "balanced_mid_first")

    assert router.metadata["active_policy_preset"] == "balanced_mid_first"
    assert set(POLICY_PRESETS) == {"fast_conservative", "balanced_mid_first", "premium_quality_first"}
