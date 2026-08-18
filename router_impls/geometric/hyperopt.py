from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import product

import numpy as np
import pandas as pd
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel

from router_impls.geometric.cross_validation import cross_validate_router


@dataclass
class HyperparamResult:
    pass_bandwidth: float
    risk_bandwidth: float
    envelope_epsilon: float
    cv_mean_score: float
    cv_std_score: float
    n_folds: int


@dataclass
class HyperparamSearchResult:
    best: HyperparamResult
    all_results: list[HyperparamResult] = field(default_factory=list)
    search_method: str = "grid"


DEFAULT_PASS_BANDWIDTH_GRID = (0.80, 1.00, 1.25, 1.50, 2.00)
DEFAULT_RISK_BANDWIDTH_GRID = (0.80, 1.00, 1.15, 1.40, 1.80)
DEFAULT_EPSILON_GRID = (1e-4, 5e-4, 1e-3, 5e-3, 1e-2)

HYPERPARAM_BOUNDS = {
    "pass_bandwidth": (0.5, 3.0),
    "risk_bandwidth": (0.5, 3.0),
    "envelope_epsilon": (1e-5, 0.1),
}


def grid_search_hyperparams(
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame | None = None,
    n_folds: int = 3,
    fallback_threshold: float = 0.85,
    radius_quantile: float = 0.90,
    include_synthetic: bool = True,
    include_smote: bool = True,
    pass_bandwidth_grid: tuple[float, ...] = DEFAULT_PASS_BANDWIDTH_GRID,
    risk_bandwidth_grid: tuple[float, ...] = DEFAULT_RISK_BANDWIDTH_GRID,
    epsilon_grid: tuple[float, ...] = DEFAULT_EPSILON_GRID,
    max_evaluations: int = 50,
) -> HyperparamSearchResult:
    all_results: list[HyperparamResult] = []
    best: HyperparamResult | None = None
    evaluated = 0

    for pass_bw, risk_bw, eps in product(pass_bandwidth_grid, risk_bandwidth_grid, epsilon_grid):
        if evaluated >= max_evaluations:
            break

        cv_result = cross_validate_router(
            train_df,
            specs_df,
            n_folds=n_folds,
            fallback_threshold=fallback_threshold,
            radius_quantile=radius_quantile,
            include_synthetic=include_synthetic,
            include_smote=include_smote,
            pass_bandwidth=pass_bw,
            risk_bandwidth=risk_bw,
            envelope_epsilon=eps,
        )

        agg = cv_result.aggregated.get("overall_weighted_score", {})
        mean_score = float(agg.get("mean", 0.0))
        std_score = float(agg.get("std", 0.0))

        result = HyperparamResult(
            pass_bandwidth=pass_bw,
            risk_bandwidth=risk_bw,
            envelope_epsilon=eps,
            cv_mean_score=mean_score,
            cv_std_score=std_score,
            n_folds=n_folds,
        )
        all_results.append(result)
        evaluated += 1

        if best is None or mean_score > best.cv_mean_score:
            best = result

    if best is None:
        best = HyperparamResult(
            pass_bandwidth=1.25,
            risk_bandwidth=1.15,
            envelope_epsilon=1e-3,
            cv_mean_score=0.0,
            cv_std_score=0.0,
            n_folds=n_folds,
        )

    return HyperparamSearchResult(
        best=best,
        all_results=all_results,
        search_method="grid",
    )


def bayesian_search_hyperparams(
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame | None = None,
    n_folds: int = 3,
    n_initial: int = 5,
    n_iterations: int = 15,
    fallback_threshold: float = 0.85,
    radius_quantile: float = 0.90,
    include_synthetic: bool = True,
    include_smote: bool = True,
    seed: int = 42,
) -> HyperparamSearchResult:
    rng = np.random.RandomState(seed)

    # Work in log-space for epsilon
    bounds_linear = [
        HYPERPARAM_BOUNDS["pass_bandwidth"],
        HYPERPARAM_BOUNDS["risk_bandwidth"],
    ]
    eps_lo, eps_hi = HYPERPARAM_BOUNDS["envelope_epsilon"]
    bounds_transformed = bounds_linear + [(math.log(eps_lo), math.log(eps_hi))]

    def _evaluate(params: np.ndarray) -> tuple[float, float]:
        pass_bw = float(params[0])
        risk_bw = float(params[1])
        eps = float(math.exp(params[2]))

        cv_result = cross_validate_router(
            train_df,
            specs_df,
            n_folds=n_folds,
            fallback_threshold=fallback_threshold,
            radius_quantile=radius_quantile,
            include_synthetic=include_synthetic,
            include_smote=include_smote,
            pass_bandwidth=pass_bw,
            risk_bandwidth=risk_bw,
            envelope_epsilon=eps,
        )
        agg = cv_result.aggregated.get("overall_weighted_score", {})
        return float(agg.get("mean", 0.0)), float(agg.get("std", 0.0))

    # Latin Hypercube initial sampling
    n_dims = 3
    initial_points: list[np.ndarray] = []
    for dim in range(n_dims):
        lo, hi = bounds_transformed[dim]
        perm = rng.permutation(n_initial)
        cuts = np.linspace(0, 1, n_initial + 1)
        values = []
        for i in range(n_initial):
            u = rng.uniform(cuts[perm[i]], cuts[perm[i] + 1])
            values.append(lo + u * (hi - lo))
        if not initial_points:
            initial_points = [np.zeros(n_dims) for _ in range(n_initial)]
        for i in range(n_initial):
            initial_points[i][dim] = values[i]

    X_observed: list[np.ndarray] = []
    y_observed: list[float] = []
    all_results: list[HyperparamResult] = []

    def _record(params: np.ndarray, mean_score: float, std_score: float) -> None:
        pass_bw = float(params[0])
        risk_bw = float(params[1])
        eps = float(math.exp(params[2]))
        all_results.append(HyperparamResult(
            pass_bandwidth=pass_bw,
            risk_bandwidth=risk_bw,
            envelope_epsilon=eps,
            cv_mean_score=mean_score,
            cv_std_score=std_score,
            n_folds=n_folds,
        ))

    for point in initial_points:
        mean_score, std_score = _evaluate(point)
        X_observed.append(point)
        y_observed.append(mean_score)
        _record(point, mean_score, std_score)

    # GP-guided iterations
    for _ in range(n_iterations):
        X_arr = np.array(X_observed, dtype=np.float64)
        y_arr = np.array(y_observed, dtype=np.float64)

        kernel = Matern(nu=2.5) + WhiteKernel(noise_level=1e-5)
        gp = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=2, random_state=seed)
        gp.fit(X_arr, y_arr)

        best_score = float(np.max(y_arr))

        candidates = np.array([
            [rng.uniform(lo, hi) for lo, hi in bounds_transformed]
            for _ in range(500)
        ], dtype=np.float64)

        mu, sigma = gp.predict(candidates, return_std=True)
        sigma = np.maximum(sigma, 1e-9)
        z = (mu - best_score) / sigma
        ei = sigma * (_standard_normal_pdf(z) + z * _standard_normal_cdf(z))
        next_idx = int(np.argmax(ei))
        next_point = candidates[next_idx]

        mean_score, std_score = _evaluate(next_point)
        X_observed.append(next_point)
        y_observed.append(mean_score)
        _record(next_point, mean_score, std_score)

    best_idx = int(np.argmax(y_observed))
    best = all_results[best_idx]

    return HyperparamSearchResult(
        best=best,
        all_results=all_results,
        search_method="bayesian",
    )


def _standard_normal_cdf(x: np.ndarray) -> np.ndarray:
    return 0.5 * (1.0 + np.vectorize(math.erf)(x / math.sqrt(2.0)))


def _standard_normal_pdf(x: np.ndarray) -> np.ndarray:
    return np.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)
