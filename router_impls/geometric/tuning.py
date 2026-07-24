from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from itertools import product

import pandas as pd

from router_impls.geometric.features import MODEL_ORDER
from router_impls.geometric.router import (
    BUDGET_LIMITS,
    DEFAULT_FALLBACK_COST_WEIGHT,
    DEFAULT_PASS_THRESHOLDS,
    DEFAULT_RADIUS_MULTIPLIERS,
    GeometricRouter,
)
from router_impls.geometric.simulator import simulate_public_set


TIER_OBJECTIVE_WEIGHTS = {
    "fast": {
        "tier_weight": 0.50,
        "cost_alpha": 1.30,
        "overflow_beta": 0.36,
        "under_gamma": 1.40,
        "over_delta": 0.08,
        "abstain_epsilon": 0.10,
    },
    "balanced": {
        "tier_weight": 0.30,
        "cost_alpha": 0.65,
        "overflow_beta": 0.18,
        "under_gamma": 1.65,
        "over_delta": 0.08,
        "abstain_epsilon": 0.10,
    },
    "premium": {
        "tier_weight": 0.20,
        "cost_alpha": 0.20,
        "overflow_beta": 0.08,
        "under_gamma": 1.90,
        "over_delta": 0.04,
        "abstain_epsilon": 0.08,
    },
}


@dataclass(frozen=True)
class TierPolicyResult:
    tier: str
    loss: float
    weighted_score: float
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
            "weighted_score": result.weighted_score,
            "objective": score_tier_summary(result.summary, tier),
            "radius_multipliers": result.radius_multipliers,
            "fallback_cost_weight": result.fallback_cost_weight,
            "pass_threshold": result.pass_threshold,
            "summary": result.summary,
        }

    router.set_policy(radius_policy, fallback_policy, pass_thresholds)
    router.metadata["policy_tuning"] = results
    router.metadata["policy_objective"] = {
        "weights": TIER_OBJECTIVE_WEIGHTS,
        "overall_score": score_policy_results(results),
    }
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
        objective = score_tier_summary(summary, tier)
        loss = -float(objective["weighted_score"])
        candidate = TierPolicyResult(
            tier=tier,
            loss=loss,
            weighted_score=float(objective["weighted_score"]),
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


def score_tier_summary(summary: dict, tier: str) -> dict:
    count = max(int(summary["count"]), 1)
    weights = TIER_OBJECTIVE_WEIGHTS[tier]
    under_rate = float(summary["under_route"]) / count
    over_rate = float(summary["over_route"]) / count
    should_abstain_rate = float(summary["should_abstain"]) / count
    overflow_ratio = float(summary["mean_excess_cost"]) / max(BUDGET_LIMITS[tier], 1e-9)
    mean_quality = float(summary["mean_quality"])
    mean_cost = float(summary["mean_cost"])
    raw_score = (
        mean_quality
        - weights["cost_alpha"] * mean_cost
        - weights["overflow_beta"] * overflow_ratio
        - weights["under_gamma"] * under_rate
        - weights["over_delta"] * over_rate
        - weights["abstain_epsilon"] * should_abstain_rate
    )
    return {
        "tier": tier,
        "raw_score": raw_score,
        "weighted_score": raw_score * weights["tier_weight"],
        "tier_weight": weights["tier_weight"],
        "components": {
            "mean_quality": mean_quality,
            "mean_cost": mean_cost,
            "overflow_ratio": overflow_ratio,
            "under_route_rate": under_rate,
            "over_route_rate": over_rate,
            "should_abstain_rate": should_abstain_rate,
        },
        "penalties": {
            "cost": weights["cost_alpha"] * mean_cost,
            "overflow": weights["overflow_beta"] * overflow_ratio,
            "under_route": weights["under_gamma"] * under_rate,
            "over_route": weights["over_delta"] * over_rate,
            "should_abstain": weights["abstain_epsilon"] * should_abstain_rate,
        },
    }


def score_policy_results(results: dict) -> float:
    return float(sum(float(result.get("weighted_score", 0.0)) for result in results.values()))


def _is_better(candidate: TierPolicyResult, best: TierPolicyResult) -> bool:
    if candidate.loss != best.loss:
        return candidate.loss < best.loss
    candidate_cost = candidate.summary["mean_cost"]
    best_cost = best.summary["mean_cost"]
    if candidate_cost != best_cost:
        return candidate_cost < best_cost
    return candidate.summary["mean_quality"] > best.summary["mean_quality"]


