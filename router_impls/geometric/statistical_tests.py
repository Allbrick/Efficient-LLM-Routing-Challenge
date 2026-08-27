from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from router_impls.geometric.features import MODEL_ORDER
from router_impls.geometric.router import GeometricRouter
from router_impls.geometric.simulator import simulate_public_set


@dataclass
class PairedTestResult:
    test_name: str
    statistic: float
    p_value: float
    significant: bool
    effect_size: float
    mean_a: float
    mean_b: float
    n_samples: int
    alpha: float = 0.05


@dataclass
class ANOVAResult:
    test_name: str
    statistic: float
    p_value: float
    significant: bool
    group_means: dict[str, float] = field(default_factory=dict)
    n_groups: int = 0
    alpha: float = 0.05


@dataclass
class ChiSquaredResult:
    test_name: str
    statistic: float
    p_value: float
    significant: bool
    dof: int = 0
    contingency_table: list[list[int]] = field(default_factory=list)
    row_labels: list[str] = field(default_factory=list)
    col_labels: list[str] = field(default_factory=list)
    alpha: float = 0.05


def paired_t_test_policies(
    router: GeometricRouter,
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame | None,
    policy_a: dict,
    policy_b: dict,
    tiers: tuple[str, ...] = ("fast", "balanced", "premium"),
    alpha: float = 0.05,
) -> PairedTestResult:
    scores_a = _simulate_per_prompt_scores(router, train_df, specs_df, policy_a, tiers)
    scores_b = _simulate_per_prompt_scores(router, train_df, specs_df, policy_b, tiers)

    common_prompts = sorted(set(scores_a.keys()) & set(scores_b.keys()))
    if len(common_prompts) < 2:
        return PairedTestResult(
            test_name="paired_t_test",
            statistic=0.0,
            p_value=1.0,
            significant=False,
            effect_size=0.0,
            mean_a=0.0,
            mean_b=0.0,
            n_samples=len(common_prompts),
            alpha=alpha,
        )

    a_vals = np.array([scores_a[pid] for pid in common_prompts], dtype=np.float64)
    b_vals = np.array([scores_b[pid] for pid in common_prompts], dtype=np.float64)

    diff = a_vals - b_vals
    diff_std = float(np.std(diff, ddof=1))

    # If all differences are zero, the distributions are identical
    if diff_std < 1e-12:
        return PairedTestResult(
            test_name="paired_t_test",
            statistic=0.0,
            p_value=1.0,
            significant=False,
            effect_size=0.0,
            mean_a=float(np.mean(a_vals)),
            mean_b=float(np.mean(b_vals)),
            n_samples=len(common_prompts),
            alpha=alpha,
        )

    t_stat, p_val = stats.ttest_rel(a_vals, b_vals)
    effect_size = float(np.mean(diff)) / diff_std

    return PairedTestResult(
        test_name="paired_t_test",
        statistic=float(t_stat),
        p_value=float(p_val),
        significant=bool(p_val < alpha),
        effect_size=effect_size,
        mean_a=float(np.mean(a_vals)),
        mean_b=float(np.mean(b_vals)),
        n_samples=len(common_prompts),
        alpha=alpha,
    )


def anova_policies(
    router: GeometricRouter,
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame | None,
    policies: dict[str, dict],
    tiers: tuple[str, ...] = ("fast", "balanced", "premium"),
    alpha: float = 0.05,
) -> ANOVAResult:
    group_scores: dict[str, list[float]] = {}
    for name, policy in policies.items():
        per_prompt = _simulate_per_prompt_scores(router, train_df, specs_df, policy, tiers)
        group_scores[name] = list(per_prompt.values())

    group_means = {name: float(np.mean(vals)) if vals else 0.0 for name, vals in group_scores.items()}

    arrays = [np.array(vals) for vals in group_scores.values() if len(vals) > 0]
    if len(arrays) < 2:
        return ANOVAResult(
            test_name="anova",
            statistic=0.0,
            p_value=1.0,
            significant=False,
            group_means=group_means,
            n_groups=len(policies),
            alpha=alpha,
        )

    f_stat, p_val = stats.f_oneway(*arrays)

    return ANOVAResult(
        test_name="anova",
        statistic=float(f_stat),
        p_value=float(p_val),
        significant=bool(p_val < alpha),
        group_means=group_means,
        n_groups=len(policies),
        alpha=alpha,
    )


def chi_squared_routing_independence(
    router: GeometricRouter,
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame | None,
    tier: str,
    alpha: float = 0.05,
) -> ChiSquaredResult:
    sim = simulate_public_set(router, train_df, specs_df, tiers=(tier,))
    rows = sim.get("rows", [])

    all_models = sorted(set(MODEL_ORDER) | {"abstain"})
    model_idx = {m: i for i, m in enumerate(all_models)}

    n = len(all_models)
    table = [[0] * n for _ in range(n)]

    for row in rows:
        if row.get("budget_tier") != tier:
            continue
        expected = str(row.get("expected_min_model", ""))
        selected = str(row.get("selected_model_id", ""))
        if expected in model_idx and selected in model_idx:
            table[model_idx[expected]][model_idx[selected]] += 1

    observed = np.array(table, dtype=np.float64)
    # Remove zero rows/columns for valid chi2
    row_sums = observed.sum(axis=1)
    col_sums = observed.sum(axis=0)
    nonzero_rows = row_sums > 0
    nonzero_cols = col_sums > 0
    filtered = observed[np.ix_(nonzero_rows, nonzero_cols)]
    filtered_row_labels = [all_models[i] for i, keep in enumerate(nonzero_rows) if keep]
    filtered_col_labels = [all_models[i] for i, keep in enumerate(nonzero_cols) if keep]

    if filtered.shape[0] < 2 or filtered.shape[1] < 2:
        return ChiSquaredResult(
            test_name="chi_squared",
            statistic=0.0,
            p_value=1.0,
            significant=False,
            dof=0,
            contingency_table=table,
            row_labels=all_models,
            col_labels=all_models,
            alpha=alpha,
        )

    chi2, p_val, dof, _ = stats.chi2_contingency(filtered)

    return ChiSquaredResult(
        test_name="chi_squared",
        statistic=float(chi2),
        p_value=float(p_val),
        significant=bool(p_val < alpha),
        dof=int(dof),
        contingency_table=filtered.astype(int).tolist(),
        row_labels=filtered_row_labels,
        col_labels=filtered_col_labels,
        alpha=alpha,
    )


def _simulate_per_prompt_scores(
    router: GeometricRouter,
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame | None,
    policy: dict,
    tiers: tuple[str, ...],
) -> dict[str, float]:
    router.set_policy(
        radius_multipliers=policy.get("radius_multipliers"),
        fallback_cost_weight=policy.get("fallback_cost_weight"),
        pass_thresholds=policy.get("pass_thresholds"),
        abstain_thresholds=policy.get("abstain_thresholds"),
    )
    sim = simulate_public_set(router, train_df, specs_df, tiers=tiers)
    per_prompt: dict[str, float] = {}
    for row in sim.get("rows", []):
        pid = str(row.get("prompt_id", ""))
        quality = float(row.get("actual_quality", 0.0))
        if pid in per_prompt:
            per_prompt[pid] = max(per_prompt[pid], quality)
        else:
            per_prompt[pid] = quality
    return per_prompt
