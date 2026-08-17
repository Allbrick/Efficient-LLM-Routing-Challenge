from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from router_impls.geometric.evaluator import build_training_labels
from router_impls.geometric.features import MODEL_ORDER


@dataclass
class DataQualityReport:
    missing_values: dict[str, Any] = field(default_factory=dict)
    quality_range: dict[str, Any] = field(default_factory=dict)
    cost_validation: dict[str, Any] = field(default_factory=dict)
    model_ordering_anomalies: list[dict[str, Any]] = field(default_factory=list)
    outliers_iqr: dict[str, Any] = field(default_factory=dict)
    outliers_esd: dict[str, Any] = field(default_factory=dict)
    class_distribution: dict[str, Any] = field(default_factory=dict)
    completeness: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "missing_values": self.missing_values,
            "quality_range": self.quality_range,
            "cost_validation": self.cost_validation,
            "model_ordering_anomalies": self.model_ordering_anomalies,
            "outliers_iqr": self.outliers_iqr,
            "outliers_esd": self.outliers_esd,
            "class_distribution": self.class_distribution,
            "completeness": self.completeness,
            "warnings": self.warnings,
            "errors": self.errors,
        }


def validate_training_data(
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame | None,
    fallback_threshold: float = 0.85,
) -> DataQualityReport:
    report = DataQualityReport()

    report.missing_values = _check_missing_values(train_df)
    report.quality_range = _validate_quality_scores(train_df)
    report.cost_validation = _validate_costs(train_df)
    report.model_ordering_anomalies = _check_model_ordering(train_df)
    report.outliers_iqr = _detect_outliers_iqr(train_df)
    report.outliers_esd = _detect_outliers_esd(train_df)
    report.class_distribution = _check_class_distribution(train_df, specs_df, fallback_threshold)
    report.completeness = _check_completeness(train_df)

    # Aggregate warnings and errors
    if report.missing_values.get("total_missing", 0) > 0:
        report.warnings.append(
            f"Found {report.missing_values['total_missing']} missing values across columns"
        )

    out_of_range = report.quality_range.get("out_of_range_count", 0)
    if out_of_range > 0:
        report.errors.append(f"Found {out_of_range} quality scores outside [0, 1]")

    negative_costs = report.cost_validation.get("negative_count", 0)
    zero_costs = report.cost_validation.get("zero_count", 0)
    if negative_costs > 0:
        report.errors.append(f"Found {negative_costs} negative cost values")
    if zero_costs > 0:
        report.warnings.append(f"Found {zero_costs} zero cost values")

    if report.model_ordering_anomalies:
        report.warnings.append(
            f"Found {len(report.model_ordering_anomalies)} prompts with quality inversions"
        )

    total_outliers_iqr = sum(
        len(v.get("indices", [])) for v in report.outliers_iqr.values() if isinstance(v, dict)
    )
    if total_outliers_iqr > 0:
        report.warnings.append(f"Found {total_outliers_iqr} IQR-based outliers in quality_score")

    total_outliers_esd = sum(
        len(v.get("indices", [])) for v in report.outliers_esd.values() if isinstance(v, dict)
    )
    if total_outliers_esd > 0:
        report.warnings.append(f"Found {total_outliers_esd} ESD-based outliers in quality_score")

    incomplete = report.completeness.get("incomplete_prompts", 0)
    if incomplete > 0:
        report.errors.append(f"Found {incomplete} prompts without exactly 3 model rows")

    duplicates = report.completeness.get("duplicate_count", 0)
    if duplicates > 0:
        report.errors.append(f"Found {duplicates} duplicate (prompt_id, model_id) pairs")

    return report


def _check_missing_values(train_df: pd.DataFrame) -> dict[str, Any]:
    null_counts = train_df.isnull().sum()
    total = len(train_df)
    per_column = {}
    for col in train_df.columns:
        count = int(null_counts[col])
        if total > 0:
            per_column[col] = {
                "count": count,
                "percentage": round(count / total * 100, 2),
            }
        else:
            per_column[col] = {"count": 0, "percentage": 0.0}
    return {
        "total_missing": int(null_counts.sum()),
        "per_column": per_column,
    }


def _validate_quality_scores(train_df: pd.DataFrame) -> dict[str, Any]:
    if "quality_score" not in train_df.columns:
        return {"error": "quality_score column not found"}

    scores = train_df["quality_score"].dropna()
    out_of_range = scores[(scores < 0.0) | (scores > 1.0)]

    per_model: dict[str, Any] = {}
    for model_id in MODEL_ORDER:
        model_scores = train_df.loc[train_df["model_id"] == model_id, "quality_score"].dropna()
        if len(model_scores) > 0:
            per_model[model_id] = {
                "count": int(len(model_scores)),
                "mean": round(float(model_scores.mean()), 4),
                "std": round(float(model_scores.std()), 4) if len(model_scores) > 1 else 0.0,
                "min": round(float(model_scores.min()), 4),
                "max": round(float(model_scores.max()), 4),
            }

    return {
        "total_scores": int(len(scores)),
        "out_of_range_count": int(len(out_of_range)),
        "out_of_range_indices": out_of_range.index.tolist(),
        "per_model": per_model,
    }


def _validate_costs(train_df: pd.DataFrame) -> dict[str, Any]:
    if "cost" not in train_df.columns:
        return {"error": "cost column not found"}

    costs = train_df["cost"].dropna()
    negative = costs[costs < 0.0]
    zero = costs[costs == 0.0]

    per_model: dict[str, Any] = {}
    for model_id in MODEL_ORDER:
        model_costs = train_df.loc[train_df["model_id"] == model_id, "cost"].dropna()
        if len(model_costs) > 0:
            per_model[model_id] = {
                "count": int(len(model_costs)),
                "mean": round(float(model_costs.mean()), 4),
                "std": round(float(model_costs.std()), 4) if len(model_costs) > 1 else 0.0,
                "min": round(float(model_costs.min()), 4),
                "max": round(float(model_costs.max()), 4),
            }

    return {
        "total_costs": int(len(costs)),
        "negative_count": int(len(negative)),
        "zero_count": int(len(zero)),
        "negative_indices": negative.index.tolist(),
        "per_model": per_model,
    }


def _check_model_ordering(train_df: pd.DataFrame) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    for prompt_id, group in train_df.groupby("prompt_id", sort=False):
        quality_by_model: dict[str, float] = {}
        for _, row in group.iterrows():
            mid = str(row.get("model_id", ""))
            qs = row.get("quality_score")
            if mid in MODEL_ORDER and qs is not None and not (isinstance(qs, float) and math.isnan(qs)):
                quality_by_model[mid] = float(qs)

        inversions: list[str] = []
        if "cheap" in quality_by_model and "mid" in quality_by_model:
            if quality_by_model["cheap"] > quality_by_model["mid"]:
                inversions.append("cheap > mid")
        if "mid" in quality_by_model and "premium" in quality_by_model:
            if quality_by_model["mid"] > quality_by_model["premium"]:
                inversions.append("mid > premium")

        if inversions:
            anomalies.append({
                "prompt_id": prompt_id,
                "quality_scores": quality_by_model,
                "inversions": inversions,
            })

    return anomalies


def _detect_outliers_iqr(train_df: pd.DataFrame) -> dict[str, Any]:
    if "quality_score" not in train_df.columns:
        return {}

    result: dict[str, Any] = {}
    for model_id in MODEL_ORDER:
        scores = train_df.loc[train_df["model_id"] == model_id, "quality_score"].dropna()
        if len(scores) < 4:
            result[model_id] = {"indices": [], "count": 0}
            continue

        q1 = float(scores.quantile(0.25))
        q3 = float(scores.quantile(0.75))
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        outliers = scores[(scores < lower) | (scores > upper)]
        result[model_id] = {
            "q1": round(q1, 4),
            "q3": round(q3, 4),
            "iqr": round(iqr, 4),
            "lower_bound": round(lower, 4),
            "upper_bound": round(upper, 4),
            "indices": outliers.index.tolist(),
            "count": int(len(outliers)),
            "values": [round(float(v), 4) for v in outliers.values],
        }

    return result


def _detect_outliers_esd(train_df: pd.DataFrame) -> dict[str, Any]:
    """Z-score > 3.0 threshold (scipy-free ESD approximation)."""
    if "quality_score" not in train_df.columns:
        return {}

    result: dict[str, Any] = {}
    z_threshold = 3.0

    for model_id in MODEL_ORDER:
        scores = train_df.loc[train_df["model_id"] == model_id, "quality_score"].dropna()
        if len(scores) < 3:
            result[model_id] = {"indices": [], "count": 0}
            continue

        mean = float(scores.mean())
        std = float(scores.std())
        if std < 1e-12:
            result[model_id] = {"indices": [], "count": 0}
            continue

        z_scores = ((scores - mean) / std).abs()
        outliers = scores[z_scores > z_threshold]
        result[model_id] = {
            "mean": round(mean, 4),
            "std": round(std, 4),
            "z_threshold": z_threshold,
            "indices": outliers.index.tolist(),
            "count": int(len(outliers)),
            "values": [round(float(v), 4) for v in outliers.values],
        }

    return result


def _check_class_distribution(
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame | None,
    fallback_threshold: float,
) -> dict[str, Any]:
    try:
        labels = build_training_labels(train_df, specs_df, fallback_threshold=fallback_threshold)
    except Exception as exc:
        return {"error": str(exc)}

    distribution = (
        labels.drop_duplicates("prompt_id")["expected_min_model"]
        .value_counts()
        .to_dict()
    )
    total = sum(distribution.values())
    percentages = {k: round(v / total * 100, 2) if total > 0 else 0.0 for k, v in distribution.items()}

    return {
        "total_prompts": total,
        "distribution": distribution,
        "percentages": percentages,
    }


def _check_completeness(train_df: pd.DataFrame) -> dict[str, Any]:
    expected_models = set(MODEL_ORDER)
    prompt_groups = train_df.groupby("prompt_id", sort=False)

    total_prompts = len(prompt_groups)
    incomplete_list: list[dict[str, Any]] = []

    for prompt_id, group in prompt_groups:
        models_present = set(group["model_id"].unique())
        if models_present != expected_models or len(group) != len(expected_models):
            incomplete_list.append({
                "prompt_id": prompt_id,
                "models_present": sorted(models_present),
                "row_count": int(len(group)),
            })

    # Detect duplicate (prompt_id, model_id) pairs
    dup_mask = train_df.duplicated(subset=["prompt_id", "model_id"], keep=False)
    duplicate_count = int(dup_mask.sum()) // 2 if int(dup_mask.sum()) > 0 else 0

    return {
        "total_prompts": total_prompts,
        "expected_models_per_prompt": sorted(expected_models),
        "incomplete_prompts": len(incomplete_list),
        "incomplete_details": incomplete_list[:20],  # cap to avoid huge reports
        "duplicate_count": duplicate_count,
    }
