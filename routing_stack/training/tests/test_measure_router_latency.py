from __future__ import annotations

import pandas as pd
import pytest

from scripts.measure_router_latency import build_latency_summary, percentile


def test_percentile_interpolates_sorted_values():
    values = [1.0, 3.0, 5.0]

    assert percentile(values, 0.0) == 1.0
    assert percentile(values, 0.5) == 3.0
    assert percentile(values, 0.95) == pytest.approx(4.8)


def test_build_latency_summary_groups_by_tier():
    detail = pd.DataFrame(
        [
            {"budget_tier": "fast", "latency_ms_mean": 1.0},
            {"budget_tier": "fast", "latency_ms_mean": 3.0},
            {"budget_tier": "balanced", "latency_ms_mean": 2.0},
        ]
    )

    summary = build_latency_summary(detail)
    fast = summary[summary["budget_tier"] == "fast"].iloc[0]

    assert fast["count"] == 2
    assert fast["latency_ms_mean"] == 2.0
    assert fast["latency_ms_p50"] == 2.0
