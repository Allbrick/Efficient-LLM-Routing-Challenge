from __future__ import annotations

import pandas as pd

from router_impls.geometric.evaluator import build_training_labels
from router_impls.geometric.features import MODEL_ORDER, MODEL_RANK
from router_impls.geometric.router import GeometricRouter


def build_sufficiency_calibration(
    router: GeometricRouter,
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame | None = None,
    bins: int = 10,
    fallback_threshold: float = 0.85,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    labels = build_training_labels(train_df, specs_df, fallback_threshold=fallback_threshold)
    label_map = labels.set_index(["prompt_id", "model_id"]).to_dict(orient="index")
    spec_map = _spec_map(specs_df)
    rows = []
    for prompt_id, group in train_df.groupby("prompt_id", sort=False):
        first = group.iloc[0]
        spec = spec_map.get(prompt_id, {})
        decision = router.route(
            str(first["prompt"]),
            budget_tier="balanced",
            task_type=str(spec.get("task_type", first.get("task_type", ""))),
            difficulty=str(spec.get("difficulty", "")),
            risk_level=str(spec.get("risk_level", "")),
            evaluation_type=str(spec.get("evaluation_type", "")),
        )
        candidates = {candidate["model_id"]: candidate for candidate in decision.candidates}
        for model_id in MODEL_ORDER:
            label = label_map.get((prompt_id, model_id), {})
            predicted = float(candidates.get(model_id, {}).get("sufficiency_probability", 0.0))
            actual = 1.0 if bool(label.get("success", False)) else 0.0
            rows.append(
                {
                    "prompt_id": prompt_id,
                    "model_id": model_id,
                    "predicted_probability": predicted,
                    "actual_success": actual,
                    "squared_error": (predicted - actual) ** 2,
                }
            )
    detail_df = pd.DataFrame(rows)
    return _bin_calibration(detail_df, bins=bins), _summarize_calibration(detail_df)


def build_ood_calibration(
    router: GeometricRouter,
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame | None = None,
    bins: int = 10,
    fallback_threshold: float = 0.85,
) -> tuple[pd.DataFrame, dict]:
    labels = build_training_labels(train_df, specs_df, fallback_threshold=fallback_threshold)
    expected_by_prompt = labels.drop_duplicates("prompt_id").set_index("prompt_id")["expected_min_model"].to_dict()
    spec_map = _spec_map(specs_df)
    rows = []
    for prompt_id, group in train_df.groupby("prompt_id", sort=False):
        first = group.iloc[0]
        spec = spec_map.get(prompt_id, {})
        decision = router.route(
            str(first["prompt"]),
            budget_tier="fast",
            task_type=str(spec.get("task_type", first.get("task_type", ""))),
            difficulty=str(spec.get("difficulty", "")),
            risk_level=str(spec.get("risk_level", "")),
            evaluation_type=str(spec.get("evaluation_type", "")),
        )
        expected = str(expected_by_prompt.get(prompt_id, "premium"))
        selected = str(decision.selected_model_id)
        cheap_label = labels[(labels["prompt_id"] == prompt_id) & (labels["model_id"] == "cheap")]
        cheap_success = bool(cheap_label["success"].any()) if not cheap_label.empty else False
        rows.append(
            {
                "prompt_id": prompt_id,
                "expected_min_model": expected,
                "selected_model_id": selected,
                "pre_route_lane": decision.evidence.get("pre_route_lane", ""),
                "ood_score": float(decision.evidence.get("ood_score", 0.0)),
                "uncertainty_score": float(decision.evidence.get("uncertainty_score", 0.0)),
                "cheap_success": 1.0 if cheap_success else 0.0,
                "cheap_direct": 1.0 if decision.evidence.get("pre_route_lane") == "cheap_direct" else 0.0,
                "premium_selected": 1.0 if selected == "premium" else 0.0,
                "under_route": 1.0 if _is_under_route(expected, selected) else 0.0,
            }
        )
    detail_df = pd.DataFrame(rows)
    binned = _bin_ood(detail_df, bins=bins)
    summary = {
        "count": int(len(detail_df)),
        "ood_high_threshold": 0.9,
        "ood_high_count": int((detail_df["ood_score"] >= 0.9).sum()) if not detail_df.empty else 0,
        "cheap_direct_success_rate": _safe_mean(
            detail_df.loc[detail_df["cheap_direct"] == 1.0, "cheap_success"]
        ),
        "ood_high_cheap_failure_rate": _safe_mean(
            1.0 - detail_df.loc[detail_df["ood_score"] >= 0.9, "cheap_success"]
        ),
        "ood_low_cheap_success_rate": _safe_mean(
            detail_df.loc[detail_df["ood_score"] < 0.3, "cheap_success"]
        ),
        "ood_high_premium_overuse_rate": _safe_mean(
            detail_df.loc[(detail_df["ood_score"] >= 0.9) & (detail_df["expected_min_model"] != "premium"), "premium_selected"]
        ),
    }
    return binned, summary


def _fill_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Fill NaN in numeric columns only.

    ``pd.cut`` produces a Categorical bin column, and calling ``fillna`` on a
    frame that still holds it raises ``TypeError`` on pandas 2.x. Restricting
    the fill to numeric columns keeps the behaviour identical on pandas 2 and 3.
    """
    numeric_columns = df.select_dtypes(include="number").columns
    if len(numeric_columns) == 0:
        return df
    df[numeric_columns] = df[numeric_columns].fillna(0.0)
    return df


def _bin_calibration(detail_df: pd.DataFrame, bins: int) -> pd.DataFrame:
    if detail_df.empty:
        return pd.DataFrame()
    df = detail_df.copy()
    df["bin"] = pd.cut(
        df["predicted_probability"],
        bins=[index / bins for index in range(bins + 1)],
        include_lowest=True,
        labels=[f"{index / bins:.1f}-{(index + 1) / bins:.1f}" for index in range(bins)],
    )
    grouped = (
        df.groupby(["model_id", "bin"], observed=False)
        .agg(
            count=("actual_success", "size"),
            mean_predicted_probability=("predicted_probability", "mean"),
            actual_success_rate=("actual_success", "mean"),
            brier_score=("squared_error", "mean"),
        )
        .reset_index()
    )
    grouped["calibration_gap"] = (
        grouped["mean_predicted_probability"] - grouped["actual_success_rate"]
    ).abs()
    return _fill_numeric(grouped)


def _summarize_calibration(detail_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for model_id, group in detail_df.groupby("model_id", sort=False):
        rows.append(
            {
                "model_id": model_id,
                "count": int(len(group)),
                "brier_score": float(group["squared_error"].mean()),
                "ece": _ece(group),
                "mean_predicted_probability": float(group["predicted_probability"].mean()),
                "actual_success_rate": float(group["actual_success"].mean()),
            }
        )
    return pd.DataFrame(rows)


def _bin_ood(detail_df: pd.DataFrame, bins: int) -> pd.DataFrame:
    if detail_df.empty:
        return pd.DataFrame()
    df = detail_df.copy()
    df["ood_bin"] = pd.cut(
        df["ood_score"],
        bins=[index / bins for index in range(bins + 1)],
        include_lowest=True,
        labels=[f"{index / bins:.1f}-{(index + 1) / bins:.1f}" for index in range(bins)],
    )
    return (
        df.groupby("ood_bin", observed=False)
        .agg(
            count=("prompt_id", "size"),
            mean_ood_score=("ood_score", "mean"),
            mean_uncertainty_score=("uncertainty_score", "mean"),
            cheap_success_rate=("cheap_success", "mean"),
            cheap_direct_rate=("cheap_direct", "mean"),
            premium_selected_rate=("premium_selected", "mean"),
            under_route_rate=("under_route", "mean"),
        )
        .reset_index()
        .pipe(_fill_numeric)
    )


def _ece(group: pd.DataFrame) -> float:
    binned = _bin_calibration(group, bins=10)
    if binned.empty:
        return 0.0
    total = float(binned["count"].sum())
    if total <= 0:
        return 0.0
    return float(((binned["count"] / total) * binned["calibration_gap"]).sum())


def _spec_map(specs_df: pd.DataFrame | None) -> dict[str, dict]:
    if specs_df is None or specs_df.empty:
        return {}
    return {row.prompt_id: row._asdict() for row in specs_df.itertuples(index=False)}


def _is_under_route(expected: str, selected: str) -> bool:
    if expected == "abstain":
        return selected != "abstain"
    if selected == "abstain":
        return True
    return MODEL_RANK[selected] < MODEL_RANK[expected]


def _safe_mean(series: pd.Series) -> float | None:
    if series.empty:
        return None
    return float(series.mean())
