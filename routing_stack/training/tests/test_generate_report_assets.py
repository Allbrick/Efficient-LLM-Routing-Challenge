from __future__ import annotations


from scripts.generate_report_assets import (
    build_before_after_summary,
    build_error_summary,
    build_selection_distribution,
    build_tier_summary,
)


def sample_tier_summary(mean_cost: float = 0.02) -> dict:
    return {
        "fast": {
            "count": 2,
            "budget_limit": 0.03,
            "mean_quality": 0.9,
            "mean_cost": mean_cost,
            "mean_excess_cost": 0.0,
            "cost_over_limit": 0,
            "under_route": 0,
            "over_route": 1,
            "should_abstain": 0,
            "ok": 1,
            "selection_counts": {"cheap": 1, "mid": 1},
        },
        "balanced": {
            "count": 2,
            "budget_limit": 0.08,
            "mean_quality": 0.92,
            "mean_cost": 0.05,
            "mean_excess_cost": 0.0,
            "cost_over_limit": 0,
            "under_route": 0,
            "over_route": 0,
            "should_abstain": 0,
            "ok": 2,
            "selection_counts": {"mid": 2},
        },
        "premium": {
            "count": 2,
            "budget_limit": 0.2,
            "mean_quality": 0.95,
            "mean_cost": 0.1,
            "mean_excess_cost": 0.0,
            "cost_over_limit": 0,
            "under_route": 0,
            "over_route": 0,
            "should_abstain": 0,
            "ok": 2,
            "selection_counts": {"premium": 2},
        },
    }


def test_build_tier_summary_includes_weighted_score():
    df = build_tier_summary(sample_tier_summary())

    assert list(df["tier"]) == ["fast", "balanced", "premium"]
    assert "weighted_score" in df.columns


def test_build_selection_distribution_counts_per_tier():
    rows = [
        {"budget_tier": "fast", "selected_model_id": "cheap", "error_type": "ok"},
        {"budget_tier": "fast", "selected_model_id": "mid", "error_type": "over_route"},
        {"budget_tier": "balanced", "selected_model_id": "mid", "error_type": "ok"},
    ]

    df = build_selection_distribution(rows)

    fast = df[df["budget_tier"] == "fast"]
    assert set(fast["selected_model_id"]) == {"cheap", "mid"}
    assert fast["ratio"].sum() == 1.0


def test_build_error_summary_counts_error_types():
    rows = [
        {"budget_tier": "fast", "selected_model_id": "cheap", "error_type": "ok"},
        {"budget_tier": "fast", "selected_model_id": "mid", "error_type": "under_route"},
    ]

    df = build_error_summary(rows)

    assert set(df["error_type"]) == {"ok", "under_route"}
    assert df["count"].sum() == 2


def test_build_before_after_summary_computes_delta():
    before = sample_tier_summary(mean_cost=0.05)
    after = sample_tier_summary(mean_cost=0.02)

    df = build_before_after_summary(before, after)
    fast = df[df["tier"] == "fast"].iloc[0]

    assert fast["delta_mean_cost"] < 0
    assert isinstance(fast["delta_weighted_score"], float)
