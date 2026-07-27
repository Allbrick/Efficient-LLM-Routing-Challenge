from __future__ import annotations

from copy import deepcopy


POLICY_PRESETS = {
    "fast_conservative": {
        "radius_multipliers": {
            "fast": {"cheap": 1.20, "mid": 0.70, "premium": 0.05},
            "balanced": {"cheap": 1.05, "mid": 0.85, "premium": 0.25},
            "premium": {"cheap": 1.00, "mid": 1.00, "premium": 0.65},
        },
        "fallback_cost_weight": {"fast": 1.35, "balanced": 0.35, "premium": 0.05},
        "pass_thresholds": {"fast": 0.88, "balanced": 0.88, "premium": 0.90},
    },
    "balanced_mid_first": {
        "radius_multipliers": {
            "fast": {"cheap": 1.15, "mid": 0.80, "premium": 0.15},
            "balanced": {"cheap": 1.00, "mid": 1.05, "premium": 0.30},
            "premium": {"cheap": 1.05, "mid": 1.05, "premium": 0.70},
        },
        "fallback_cost_weight": {"fast": 1.0, "balanced": 0.50, "premium": 0.05},
        "pass_thresholds": {"fast": 0.86, "balanced": 0.84, "premium": 0.90},
    },
    "premium_quality_first": {
        "radius_multipliers": {
            "fast": {"cheap": 1.10, "mid": 0.85, "premium": 0.20},
            "balanced": {"cheap": 1.00, "mid": 0.90, "premium": 0.45},
            "premium": {"cheap": 0.95, "mid": 1.00, "premium": 0.95},
        },
        "fallback_cost_weight": {"fast": 0.80, "balanced": 0.20, "premium": 0.0},
        "pass_thresholds": {"fast": 0.84, "balanced": 0.86, "premium": 0.88},
    },
}


def apply_policy_preset(router, preset_name: str):
    if preset_name not in POLICY_PRESETS:
        raise ValueError(f"unknown policy preset: {preset_name}")
    preset = deepcopy(POLICY_PRESETS[preset_name])
    router.set_policy(
        radius_multipliers=preset.get("radius_multipliers"),
        fallback_cost_weight=preset.get("fallback_cost_weight"),
        pass_thresholds=preset.get("pass_thresholds"),
    )
    router.metadata.setdefault("policy_presets", {})
    router.metadata["active_policy_preset"] = preset_name
    return router
