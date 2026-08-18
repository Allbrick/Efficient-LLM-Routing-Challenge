from __future__ import annotations

from copy import deepcopy

import numpy as np

from router_impls.geometric.bayesian_tuning import (
    TIER_BOUNDS,
    BayesianTuningConfig,
    bayesian_tune_tier_policy,
)
from router_impls.geometric.cross_validation import cross_validate_router
from router_impls.geometric.hyperopt import (
    grid_search_hyperparams,
    bayesian_search_hyperparams,
)
from router_impls.geometric.pass_model import fit_pass_model
from router_impls.geometric.risk_model import fit_risk_model
from router_impls.geometric.router import (
    DEFAULT_FALLBACK_COST_WEIGHT,
    DEFAULT_PASS_THRESHOLDS,
    DEFAULT_RADIUS_MULTIPLIERS,
    GeometricRouter,
)
from router_impls.geometric.statistical_tests import (
    anova_policies,
    chi_squared_routing_independence,
    paired_t_test_policies,
)
from router_impls.geometric.tests.test_geometric_router import load_data, make_router
from router_impls.geometric.tuning import _tier_grid


# -- Parameter flow tests -------------------------------------------------------


def test_fit_pass_model_respects_bandwidth():
    train_df, specs_df = load_data()
    router = make_router()
    # Build minimal features for pass model
    from router_impls.geometric.evaluator import build_training_labels
    from router_impls.geometric.features import EvidenceExtractor

    labels = build_training_labels(train_df, specs_df)
    extractor = EvidenceExtractor()
    prompt_features = {}
    for prompt_id, group in train_df.groupby("prompt_id", sort=False):
        first = group.iloc[0]
        evidence = extractor.transform(str(first["prompt"]))
        prompt_features[str(prompt_id)] = evidence.as_vector()

    model = fit_pass_model(prompt_features, labels, bandwidth=2.0)
    assert model.bandwidth == 2.0


def test_fit_risk_model_respects_bandwidth():
    train_df, specs_df = load_data()
    from router_impls.geometric.evaluator import build_training_labels
    from router_impls.geometric.features import EvidenceExtractor

    labels = build_training_labels(train_df, specs_df)
    extractor = EvidenceExtractor()
    prompt_features = {}
    prompt_texts = {}
    for prompt_id, group in train_df.groupby("prompt_id", sort=False):
        first = group.iloc[0]
        prompt_texts[str(prompt_id)] = str(first["prompt"])
        evidence = extractor.transform(str(first["prompt"]))
        prompt_features[str(prompt_id)] = evidence.as_vector()

    model = fit_risk_model(prompt_features, labels, prompt_texts, bandwidth=2.0)
    assert model.bandwidth == 2.0


def test_router_fit_threads_bandwidth_and_epsilon():
    train_df, specs_df = load_data()
    router = GeometricRouter.fit(
        train_df, specs_df,
        pass_bandwidth=1.80,
        risk_bandwidth=1.50,
        envelope_epsilon=5e-3,
    )
    assert router.pass_model is not None
    assert router.pass_model.bandwidth == 1.80
    assert router.risk_model is not None
    assert router.risk_model.bandwidth == 1.50
    assert router.metadata["pass_bandwidth"] == 1.80
    assert router.metadata["risk_bandwidth"] == 1.50
    assert router.metadata["envelope_epsilon"] == 5e-3


def test_cross_validation_passes_hyperparams():
    train_df, specs_df = load_data()
    result = cross_validate_router(
        train_df, specs_df,
        n_folds=2,
        pass_bandwidth=1.50,
        risk_bandwidth=1.30,
        envelope_epsilon=5e-3,
    )
    assert result.n_folds == 2
    assert len(result.fold_results) == 2
    agg = result.aggregated.get("overall_weighted_score", {})
    assert "mean" in agg


# -- Bayesian tuning tests ------------------------------------------------------


def test_bayesian_tune_tier_returns_valid_result():
    train_df, specs_df = load_data()
    router = make_router()
    config = BayesianTuningConfig(n_initial=3, n_iterations=2, seed=42)
    result = bayesian_tune_tier_policy(
        router, train_df, specs_df,
        tier="fast",
        base_radius_policy=deepcopy(DEFAULT_RADIUS_MULTIPLIERS),
        base_fallback_policy=DEFAULT_FALLBACK_COST_WEIGHT.copy(),
        base_pass_thresholds=DEFAULT_PASS_THRESHOLDS.copy(),
        config=config,
    )
    assert result.tier == "fast"
    assert isinstance(result.radius_multipliers, dict)
    assert "cheap" in result.radius_multipliers
    assert "mid" in result.radius_multipliers
    assert "premium" in result.radius_multipliers
    assert isinstance(result.fallback_cost_weight, float)
    assert isinstance(result.pass_threshold, float)


def test_bayesian_tune_compatible_with_grid_format():
    train_df, specs_df = load_data()
    router = make_router()
    config = BayesianTuningConfig(n_initial=3, n_iterations=2, seed=42)
    result = bayesian_tune_tier_policy(
        router, train_df, specs_df,
        tier="balanced",
        base_radius_policy=deepcopy(DEFAULT_RADIUS_MULTIPLIERS),
        base_fallback_policy=DEFAULT_FALLBACK_COST_WEIGHT.copy(),
        base_pass_thresholds=DEFAULT_PASS_THRESHOLDS.copy(),
        config=config,
    )
    # Should have same attributes as TierPolicyResult from grid search
    assert hasattr(result, "tier")
    assert hasattr(result, "loss")
    assert hasattr(result, "weighted_score")
    assert hasattr(result, "radius_multipliers")
    assert hasattr(result, "fallback_cost_weight")
    assert hasattr(result, "pass_threshold")
    assert hasattr(result, "summary")


def test_tier_bounds_cover_grid_values():
    for tier in ("fast", "balanced", "premium"):
        bounds = TIER_BOUNDS[tier]
        grid_values = list(_tier_grid(tier))
        for combo in grid_values:
            cheap, mid, premium, fallback, pass_t = combo
            assert bounds["cheap_mult"][0] <= cheap <= bounds["cheap_mult"][1], f"{tier} cheap={cheap} out of bounds"
            assert bounds["mid_mult"][0] <= mid <= bounds["mid_mult"][1], f"{tier} mid={mid} out of bounds"
            assert bounds["premium_mult"][0] <= premium <= bounds["premium_mult"][1], f"{tier} premium={premium} out of bounds"
            assert bounds["fallback_weight"][0] <= fallback <= bounds["fallback_weight"][1], f"{tier} fallback={fallback} out of bounds"
            assert bounds["pass_threshold"][0] <= pass_t <= bounds["pass_threshold"][1], f"{tier} pass_t={pass_t} out of bounds"


def test_bayesian_tune_produces_positive_score():
    train_df, specs_df = load_data()
    router = make_router()
    config = BayesianTuningConfig(n_initial=3, n_iterations=2, seed=42)
    result = bayesian_tune_tier_policy(
        router, train_df, specs_df,
        tier="balanced",
        base_radius_policy=deepcopy(DEFAULT_RADIUS_MULTIPLIERS),
        base_fallback_policy=DEFAULT_FALLBACK_COST_WEIGHT.copy(),
        base_pass_thresholds=DEFAULT_PASS_THRESHOLDS.copy(),
        config=config,
    )
    assert result.weighted_score > 0


# -- Hyperparameter optimization tests ------------------------------------------


def test_grid_search_hyperparams_returns_result():
    train_df, specs_df = load_data()
    result = grid_search_hyperparams(
        train_df, specs_df,
        n_folds=2,
        pass_bandwidth_grid=(1.00, 1.25),
        risk_bandwidth_grid=(1.00,),
        epsilon_grid=(1e-3,),
        max_evaluations=2,
    )
    assert result.best is not None
    assert result.search_method == "grid"
    assert len(result.all_results) <= 2


def test_grid_search_best_has_valid_ranges():
    train_df, specs_df = load_data()
    result = grid_search_hyperparams(
        train_df, specs_df,
        n_folds=2,
        pass_bandwidth_grid=(1.00, 1.25),
        risk_bandwidth_grid=(1.00, 1.15),
        epsilon_grid=(1e-3,),
        max_evaluations=4,
    )
    best = result.best
    assert best.pass_bandwidth in (1.00, 1.25)
    assert best.risk_bandwidth in (1.00, 1.15)
    assert best.envelope_epsilon == 1e-3


def test_bayesian_search_hyperparams_returns_result():
    train_df, specs_df = load_data()
    result = bayesian_search_hyperparams(
        train_df, specs_df,
        n_folds=2,
        n_initial=2,
        n_iterations=1,
    )
    assert result.best is not None
    assert result.search_method == "bayesian"
    assert len(result.all_results) == 3  # 2 initial + 1 iteration


# -- Statistical tests -----------------------------------------------------------


def test_paired_t_test_identical_policies():
    train_df, specs_df = load_data()
    router = make_router()
    policy = {
        "radius_multipliers": deepcopy(router.radius_multipliers),
        "fallback_cost_weight": router.fallback_cost_weight.copy(),
        "pass_thresholds": router.pass_thresholds.copy(),
    }
    result = paired_t_test_policies(
        router, train_df, specs_df,
        policy_a=policy,
        policy_b=policy,
    )
    assert result.test_name == "paired_t_test"
    assert result.p_value > 0.05
    assert not result.significant


def test_chi_squared_returns_valid_structure():
    train_df, specs_df = load_data()
    router = make_router()
    result = chi_squared_routing_independence(router, train_df, specs_df, tier="balanced")
    assert result.test_name == "chi_squared"
    assert result.dof >= 0
    assert len(result.row_labels) > 0
    assert len(result.col_labels) > 0


def test_anova_returns_valid_structure():
    train_df, specs_df = load_data()
    router = make_router()
    policy = {
        "radius_multipliers": deepcopy(router.radius_multipliers),
        "fallback_cost_weight": router.fallback_cost_weight.copy(),
        "pass_thresholds": router.pass_thresholds.copy(),
    }
    result = anova_policies(
        router, train_df, specs_df,
        policies={"default": policy, "same": policy},
    )
    assert result.test_name == "anova"
    assert len(result.group_means) == 2
    assert "default" in result.group_means
    assert "same" in result.group_means
