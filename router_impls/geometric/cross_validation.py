from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold, StratifiedKFold

from router_impls.geometric.evaluator import build_training_labels
from router_impls.geometric.router import GeometricRouter
from router_impls.geometric.simulator import simulate_public_set
from router_impls.geometric.tuning import score_tier_summary


@dataclass
class FoldResult:
    fold_index: int
    n_train_prompts: int
    n_val_prompts: int
    tier_summary: dict[str, Any]
    fit_time_seconds: float
    simulate_time_seconds: float


@dataclass
class CrossValidationResult:
    n_folds: int
    fold_results: list[FoldResult] = field(default_factory=list)
    aggregated: dict[str, Any] = field(default_factory=dict)
    total_time_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_folds": self.n_folds,
            "fold_results": [
                {
                    "fold_index": fr.fold_index,
                    "n_train_prompts": fr.n_train_prompts,
                    "n_val_prompts": fr.n_val_prompts,
                    "tier_summary": fr.tier_summary,
                    "fit_time_seconds": round(fr.fit_time_seconds, 3),
                    "simulate_time_seconds": round(fr.simulate_time_seconds, 3),
                }
                for fr in self.fold_results
            ],
            "aggregated": self.aggregated,
            "total_time_seconds": round(self.total_time_seconds, 3),
        }


def cross_validate_router(
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame | None = None,
    n_folds: int = 5,
    fallback_threshold: float = 0.85,
    radius_quantile: float = 0.90,
    include_synthetic: bool = True,
    tiers: tuple[str, ...] = ("fast", "balanced", "premium"),
) -> CrossValidationResult:
    total_start = time.time()

    # Build labels to get expected_min_model for stratification
    labels = build_training_labels(train_df, specs_df, fallback_threshold=fallback_threshold)
    prompt_labels = labels.drop_duplicates("prompt_id")[["prompt_id", "expected_min_model"]]
    prompt_ids = prompt_labels["prompt_id"].values
    stratify_labels = prompt_labels["expected_min_model"].values

    # Use StratifiedKFold if possible, fall back to KFold if any class is too small
    n_folds = min(n_folds, len(prompt_ids))
    try:
        # Check if any class has fewer members than n_folds
        from collections import Counter

        class_counts = Counter(stratify_labels)
        min_class_count = min(class_counts.values())
        if min_class_count < n_folds:
            splitter = KFold(n_splits=n_folds, shuffle=True, random_state=42)
            splits = list(splitter.split(prompt_ids))
        else:
            splitter = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)
            splits = list(splitter.split(prompt_ids, stratify_labels))
    except ValueError:
        splitter = KFold(n_splits=n_folds, shuffle=True, random_state=42)
        splits = list(splitter.split(prompt_ids))

    fold_results: list[FoldResult] = []

    for fold_idx, (train_indices, val_indices) in enumerate(splits):
        train_prompt_ids = set(prompt_ids[train_indices])
        val_prompt_ids = set(prompt_ids[val_indices])

        fold_train_df = train_df[train_df["prompt_id"].isin(train_prompt_ids)].copy()
        fold_val_df = train_df[train_df["prompt_id"].isin(val_prompt_ids)].copy()

        # Filter specs_df to only include train prompts for fitting
        fold_specs_df = None
        if specs_df is not None and not specs_df.empty:
            fold_train_specs = specs_df[specs_df["prompt_id"].isin(train_prompt_ids)].copy()
            fold_specs_df = fold_train_specs if not fold_train_specs.empty else None

        # Fit router on fold training data (synthetic data added inside fit)
        fit_start = time.time()
        fold_router = GeometricRouter.fit(
            fold_train_df,
            fold_specs_df,
            fallback_threshold=fallback_threshold,
            radius_quantile=radius_quantile,
            include_synthetic=include_synthetic,
        )
        fit_time = time.time() - fit_start

        # Simulate on held-out validation data
        # Use full specs for validation evaluation (ground truth labels)
        val_specs_df = None
        if specs_df is not None and not specs_df.empty:
            val_specs = specs_df[specs_df["prompt_id"].isin(val_prompt_ids)].copy()
            val_specs_df = val_specs if not val_specs.empty else None

        sim_start = time.time()
        sim_result = simulate_public_set(
            fold_router,
            fold_val_df,
            val_specs_df,
            tiers=tiers,
            fallback_threshold=fallback_threshold,
        )
        simulate_time = time.time() - sim_start

        fold_results.append(
            FoldResult(
                fold_index=fold_idx,
                n_train_prompts=len(train_prompt_ids),
                n_val_prompts=len(val_prompt_ids),
                tier_summary=sim_result["summary"]["tier_summary"],
                fit_time_seconds=fit_time,
                simulate_time_seconds=simulate_time,
            )
        )

    # Aggregate: mean +/- std for each tier metric + weighted_score
    aggregated = _aggregate_fold_results(fold_results, tiers)

    total_time = time.time() - total_start
    return CrossValidationResult(
        n_folds=n_folds,
        fold_results=fold_results,
        aggregated=aggregated,
        total_time_seconds=total_time,
    )


def _aggregate_fold_results(
    fold_results: list[FoldResult],
    tiers: tuple[str, ...],
) -> dict[str, Any]:
    aggregated: dict[str, Any] = {}

    for tier in tiers:
        tier_metrics: dict[str, list[float]] = {
            "mean_quality": [],
            "mean_cost": [],
            "mean_excess_cost": [],
            "under_route": [],
            "over_route": [],
            "should_abstain": [],
            "ok": [],
            "weighted_score": [],
        }

        for fr in fold_results:
            ts = fr.tier_summary.get(tier)
            if ts is None:
                continue
            for key in ("mean_quality", "mean_cost", "mean_excess_cost"):
                tier_metrics[key].append(float(ts.get(key, 0.0)))
            for key in ("under_route", "over_route", "should_abstain", "ok"):
                tier_metrics[key].append(int(ts.get(key, 0)))
            # Compute weighted_score via score_tier_summary
            scored = score_tier_summary(ts, tier)
            tier_metrics["weighted_score"].append(float(scored["weighted_score"]))

        tier_agg: dict[str, Any] = {}
        for metric, values in tier_metrics.items():
            if not values:
                tier_agg[metric] = {"mean": 0.0, "std": 0.0}
            else:
                arr = np.array(values, dtype=float)
                tier_agg[metric] = {
                    "mean": round(float(arr.mean()), 4),
                    "std": round(float(arr.std()), 4),
                }

        aggregated[tier] = tier_agg

    # Overall weighted score across tiers
    overall_scores: list[float] = []
    for fr in fold_results:
        fold_total = 0.0
        for tier in tiers:
            ts = fr.tier_summary.get(tier)
            if ts is not None:
                scored = score_tier_summary(ts, tier)
                fold_total += float(scored["weighted_score"])
        overall_scores.append(fold_total)

    if overall_scores:
        arr = np.array(overall_scores, dtype=float)
        aggregated["overall_weighted_score"] = {
            "mean": round(float(arr.mean()), 4),
            "std": round(float(arr.std()), 4),
        }
    else:
        aggregated["overall_weighted_score"] = {"mean": 0.0, "std": 0.0}

    return aggregated
