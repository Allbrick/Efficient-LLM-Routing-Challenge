from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from itertools import product

import pandas as pd

from geometric_router.features import MODEL_ORDER
from geometric_router.router import (
    BUDGET_LIMITS,
    DEFAULT_FALLBACK_COST_WEIGHT,
    DEFAULT_PASS_THRESHOLDS,
    DEFAULT_RADIUS_MULTIPLIERS,
    GeometricRouter,
)
from geometric_router.simulator import simulate_public_set


@dataclass(frozen=True)
class TierPolicyResult:
    tier: str
    loss: float
    radius_multipliers: dict[str, float]
    fallback_cost_weight: float
    pass_threshold: float
    summary: dict


def tune_router_policy(
    router: GeometricRouter,
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame | None = None,
    tiers: tuple[str, ...] = ("fast", "balanced", "premium"),
) -> dict:
    radius_policy = deepcopy(DEFAULT_RADIUS_MULTIPLIERS)
    fallback_policy = DEFAULT_FALLBACK_COST_WEIGHT.copy()
    pass_thresholds = DEFAULT_PASS_THRESHOLDS.copy()
    results = {}

    for tier in tiers:
        result = tune_tier_policy(router, train_df, specs_df, tier, radius_policy, fallback_policy, pass_thresholds)
        radius_policy[tier] = result.radius_multipliers
        fallback_policy[tier] = result.fallback_cost_weight
        pass_thresholds[tier] = result.pass_threshold
        results[tier] = {
            "loss": result.loss,
            "radius_multipliers": result.radius_multipliers,
            "fallback_cost_weight": result.fallback_cost_weight,
            "pass_threshold": result.pass_threshold,
            "summary": result.summary,
        }

    router.set_policy(radius_policy, fallback_policy, pass_thresholds)
    router.metadata["policy_tuning"] = results
    return results


def tune_tier_policy(
    router: GeometricRouter,
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame | None,
    tier: str,
    base_radius_policy: dict[str, dict[str, float]],
    base_fallback_policy: dict[str, float],
    base_pass_thresholds: dict[str, float],
) -> TierPolicyResult:
    grid = _tier_grid(tier)
    best: TierPolicyResult | None = None

    for cheap_mult, mid_mult, premium_mult, fallback_weight, pass_threshold in grid:
        radius_policy = deepcopy(base_radius_policy)
        fallback_policy = base_fallback_policy.copy()
        pass_thresholds = base_pass_thresholds.copy()
        radius_policy[tier] = {
            "cheap": cheap_mult,
            "mid": mid_mult,
            "premium": premium_mult,
        }
        fallback_policy[tier] = fallback_weight
        pass_thresholds[tier] = pass_threshold
        router.set_policy(radius_policy, fallback_policy, pass_thresholds)
        payload = simulate_public_set(router, train_df, specs_df, tiers=(tier,))
        summary = payload["summary"]["tier_summary"][tier]
        loss = _tier_loss(summary, tier)
        candidate = TierPolicyResult(
            tier=tier,
            loss=loss,
            radius_multipliers=radius_policy[tier],
            fallback_cost_weight=fallback_weight,
            pass_threshold=pass_threshold,
            summary=summary,
        )
        if best is None or _is_better(candidate, best):
            best = candidate

    if best is None:
        raise RuntimeError(f"no policy candidates evaluated for {tier}")
    router.set_policy(base_radius_policy, base_fallback_policy, base_pass_thresholds)
    return best


def _tier_grid(tier: str):
    if tier == "fast":
        cheap_values = (0.95, 1.15)
        mid_values = (0.45, 0.80)
        premium_values = (0.15, 0.40)
        fallback_values = (1.0, 4.0)
        pass_values = (0.86, 0.96)
    elif tier == "balanced":
        cheap_values = (0.95, 1.10)
        mid_values = (0.75, 1.00)
        premium_values = (0.35, 0.75)
        fallback_values = (0.25, 1.0)
        pass_values = (0.86, 0.96)
    else:
        cheap_values = (0.90, 1.10)
        mid_values = (0.80, 1.05)
        premium_values = (0.70, 1.10)
        fallback_values = (0.0, 0.50)
        pass_values = (0.90, 0.98)
    return product(cheap_values, mid_values, premium_values, fallback_values, pass_values)


def _tier_loss(summary: dict, tier: str) -> float:
    count = max(int(summary["count"]), 1)
    under = summary["under_route"] / count
    over = summary["over_route"] / count
    excess = summary["mean_excess_cost"] / max(BUDGET_LIMITS[tier], 1e-9)
    quality_gap = max(0.0, 0.90 - float(summary["mean_quality"]))

    if tier == "fast":
        return 5.0 * under + 12.0 * excess + 0.4 * over + 1.5 * quality_gap
    if tier == "balanced":
        return 8.0 * under + 2.0 * excess + 0.5 * over + 2.5 * quality_gap
    return 10.0 * under + 0.5 * excess + 0.25 * over + 3.0 * quality_gap


def _is_better(candidate: TierPolicyResult, best: TierPolicyResult) -> bool:
    if candidate.loss != best.loss:
        return candidate.loss < best.loss
    candidate_cost = candidate.summary["mean_cost"]
    best_cost = best.summary["mean_cost"]
    if candidate_cost != best_cost:
        return candidate_cost < best_cost
    return candidate.summary["mean_quality"] > best.summary["mean_quality"]
