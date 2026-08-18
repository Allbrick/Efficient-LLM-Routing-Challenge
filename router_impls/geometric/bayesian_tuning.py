from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel

from router_impls.geometric.router import (
    DEFAULT_FALLBACK_COST_WEIGHT,
    DEFAULT_PASS_THRESHOLDS,
    DEFAULT_RADIUS_MULTIPLIERS,
    GeometricRouter,
)
from router_impls.geometric.simulator import simulate_public_set
from router_impls.geometric.tuning import (
    TierPolicyResult,
    score_policy_results,
    score_tier_summary,
)


@dataclass
class BayesianTuningConfig:
    n_initial: int = 10
    n_iterations: int = 30
    seed: int = 42


TIER_BOUNDS: dict[str, dict[str, tuple[float, float]]] = {
    "fast": {
        "cheap_mult": (0.80, 1.30),
        "mid_mult": (0.30, 1.00),
        "premium_mult": (0.05, 0.50),
        "fallback_weight": (0.50, 6.00),
        "pass_threshold": (0.80, 0.98),
    },
    "balanced": {
        "cheap_mult": (0.80, 1.20),
        "mid_mult": (0.60, 1.15),
        "premium_mult": (0.20, 0.90),
        "fallback_weight": (0.10, 2.00),
        "pass_threshold": (0.80, 0.98),
    },
    "premium": {
        "cheap_mult": (0.75, 1.20),
        "mid_mult": (0.70, 1.15),
        "premium_mult": (0.50, 1.20),
        "fallback_weight": (0.00, 1.00),
        "pass_threshold": (0.85, 0.99),
    },
}

PARAM_NAMES = ("cheap_mult", "mid_mult", "premium_mult", "fallback_weight", "pass_threshold")


def bayesian_tune_router_policy(
    router: GeometricRouter,
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame | None = None,
    config: BayesianTuningConfig | None = None,
    tiers: tuple[str, ...] = ("fast", "balanced", "premium"),
) -> dict:
    if config is None:
        config = BayesianTuningConfig()

    radius_policy = deepcopy(DEFAULT_RADIUS_MULTIPLIERS)
    fallback_policy = DEFAULT_FALLBACK_COST_WEIGHT.copy()
    pass_thresholds = DEFAULT_PASS_THRESHOLDS.copy()
    results: dict = {}

    for tier in tiers:
        result = bayesian_tune_tier_policy(
            router, train_df, specs_df, tier,
            radius_policy, fallback_policy, pass_thresholds,
            config,
        )
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
    router.metadata["policy_tuning_method"] = "bayesian"
    router.metadata["policy_objective"] = {
        "weights": {},
        "overall_score": score_policy_results(results),
    }
    return results


def bayesian_tune_tier_policy(
    router: GeometricRouter,
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame | None,
    tier: str,
    base_radius_policy: dict[str, dict[str, float]],
    base_fallback_policy: dict[str, float],
    base_pass_thresholds: dict[str, float],
    config: BayesianTuningConfig | None = None,
) -> TierPolicyResult:
    if config is None:
        config = BayesianTuningConfig()

    bounds = TIER_BOUNDS.get(tier, TIER_BOUNDS["balanced"])
    bound_list = [bounds[name] for name in PARAM_NAMES]
    rng = np.random.RandomState(config.seed)

    # Phase 1: Latin Hypercube Sampling for initial points
    initial_points = _latin_hypercube_sample(bound_list, config.n_initial, rng)

    X_observed: list[np.ndarray] = []
    y_observed: list[float] = []

    def _evaluate(params: np.ndarray) -> float:
        cheap_mult, mid_mult, premium_mult, fallback_weight, pass_threshold = params
        radius_policy = deepcopy(base_radius_policy)
        fallback_policy = base_fallback_policy.copy()
        pass_thresholds = base_pass_thresholds.copy()
        radius_policy[tier] = {
            "cheap": float(cheap_mult),
            "mid": float(mid_mult),
            "premium": float(premium_mult),
        }
        fallback_policy[tier] = float(fallback_weight)
        pass_thresholds[tier] = float(pass_threshold)
        router.set_policy(radius_policy, fallback_policy, pass_thresholds)
        payload = simulate_public_set(router, train_df, specs_df, tiers=(tier,))
        summary = payload["summary"]["tier_summary"][tier]
        objective = score_tier_summary(summary, tier)
        return float(objective["weighted_score"])

    # Evaluate initial points
    for point in initial_points:
        score = _evaluate(point)
        X_observed.append(point)
        y_observed.append(score)

    # Phase 2: GP-guided iterations
    for _ in range(config.n_iterations):
        X_arr = np.array(X_observed, dtype=np.float64)
        y_arr = np.array(y_observed, dtype=np.float64)

        kernel = Matern(nu=2.5) + WhiteKernel(noise_level=1e-5)
        gp = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=2, random_state=config.seed)
        gp.fit(X_arr, y_arr)

        best_score = float(np.max(y_arr))

        # Pick next point by maximizing EI over random candidates
        candidates = np.array([
            [rng.uniform(lo, hi) for lo, hi in bound_list]
            for _ in range(500)
        ], dtype=np.float64)

        ei_values = _expected_improvement(candidates, gp, best_score)
        next_idx = int(np.argmax(ei_values))
        next_point = candidates[next_idx]

        score = _evaluate(next_point)
        X_observed.append(next_point)
        y_observed.append(score)

    # Restore policy and find best result
    router.set_policy(base_radius_policy, base_fallback_policy, base_pass_thresholds)

    best_idx = int(np.argmax(y_observed))
    best_params = X_observed[best_idx]
    cheap_mult, mid_mult, premium_mult, fallback_weight, pass_threshold = best_params

    # Re-evaluate best to get summary
    radius_policy = deepcopy(base_radius_policy)
    fallback_policy = base_fallback_policy.copy()
    pass_thresholds = base_pass_thresholds.copy()
    radius_policy[tier] = {
        "cheap": float(cheap_mult),
        "mid": float(mid_mult),
        "premium": float(premium_mult),
    }
    fallback_policy[tier] = float(fallback_weight)
    pass_thresholds[tier] = float(pass_threshold)
    router.set_policy(radius_policy, fallback_policy, pass_thresholds)
    payload = simulate_public_set(router, train_df, specs_df, tiers=(tier,))
    summary = payload["summary"]["tier_summary"][tier]
    router.set_policy(base_radius_policy, base_fallback_policy, base_pass_thresholds)

    return TierPolicyResult(
        tier=tier,
        loss=-y_observed[best_idx],
        weighted_score=y_observed[best_idx],
        radius_multipliers=radius_policy[tier],
        fallback_cost_weight=float(fallback_weight),
        pass_threshold=float(pass_threshold),
        summary=summary,
    )


def _expected_improvement(
    X_new: np.ndarray,
    gp: GaussianProcessRegressor,
    best_score: float,
) -> np.ndarray:
    mu, sigma = gp.predict(X_new, return_std=True)
    sigma = np.maximum(sigma, 1e-9)
    z = (mu - best_score) / sigma
    ei = sigma * (_standard_normal_pdf(z) + z * _standard_normal_cdf(z))
    return ei


def _standard_normal_cdf(x: np.ndarray) -> np.ndarray:
    return 0.5 * (1.0 + _erf_array(x / math.sqrt(2.0)))


def _standard_normal_pdf(x: np.ndarray) -> np.ndarray:
    return np.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _erf_array(x: np.ndarray) -> np.ndarray:
    return np.vectorize(math.erf)(x)


def _latin_hypercube_sample(
    bounds: list[tuple[float, float]],
    n_samples: int,
    rng: np.random.RandomState,
) -> list[np.ndarray]:
    n_dims = len(bounds)
    result: list[np.ndarray] = []
    for dim in range(n_dims):
        lo, hi = bounds[dim]
        perm = rng.permutation(n_samples)
        cuts = np.linspace(0, 1, n_samples + 1)
        values = []
        for i in range(n_samples):
            u = rng.uniform(cuts[perm[i]], cuts[perm[i] + 1])
            values.append(lo + u * (hi - lo))
        if not result:
            result = [np.zeros(n_dims) for _ in range(n_samples)]
        for i in range(n_samples):
            result[i][dim] = values[i]
    return result
