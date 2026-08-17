from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score

from router_impls.geometric.evaluator import build_training_labels
from router_impls.geometric.features import MODEL_ORDER
from router_impls.geometric.router import GeometricRouter

ROUTING_LABELS = ("abstain", "cheap", "mid", "premium")


def compute_routing_confusion_matrix(
    simulation_rows: list[dict[str, Any]],
    tier: str | None = None,
) -> dict[str, Any]:
    rows = simulation_rows
    if tier is not None:
        rows = [r for r in rows if r.get("budget_tier") == tier]

    y_true = [r["expected_min_model"] for r in rows]
    y_pred = [r["selected_model_id"] for r in rows]

    labels = list(ROUTING_LABELS)
    cm = confusion_matrix(y_true, y_pred, labels=labels)

    return {
        "labels": labels,
        "matrix": cm.tolist(),
        "tier": tier,
        "total_samples": len(rows),
    }


def compute_classification_report(
    simulation_rows: list[dict[str, Any]],
    tier: str | None = None,
) -> dict[str, Any]:
    rows = simulation_rows
    if tier is not None:
        rows = [r for r in rows if r.get("budget_tier") == tier]

    y_true = [r["expected_min_model"] for r in rows]
    y_pred = [r["selected_model_id"] for r in rows]

    labels = list(ROUTING_LABELS)
    report = classification_report(
        y_true,
        y_pred,
        labels=labels,
        output_dict=True,
        zero_division=0,
    )

    return {
        "per_class": {label: report[label] for label in labels if label in report},
        "accuracy": report.get("accuracy", 0.0),
        "macro_avg": report.get("macro avg", {}),
        "weighted_avg": report.get("weighted avg", {}),
        "tier": tier,
        "total_samples": len(rows),
    }


def compute_roc_auc(
    router: GeometricRouter,
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame | None = None,
    fallback_threshold: float = 0.85,
) -> dict[str, Any]:
    labels = build_training_labels(train_df, specs_df, fallback_threshold=fallback_threshold)
    expected_by_prompt = (
        labels.drop_duplicates("prompt_id")
        .set_index("prompt_id")["expected_min_model"]
        .to_dict()
    )

    spec_map: dict[str, dict] = {}
    if specs_df is not None and not specs_df.empty:
        spec_map = {row.prompt_id: row._asdict() for row in specs_df.itertuples(index=False)}

    # Collect pass probabilities and ground truth per model
    model_scores: dict[str, dict[str, list]] = {
        model: {"y_true": [], "y_score": []} for model in MODEL_ORDER
    }

    for prompt_id, group in train_df.groupby("prompt_id", sort=False):
        first = group.iloc[0]
        spec = spec_map.get(prompt_id, {})
        expected = expected_by_prompt.get(prompt_id, "premium")

        decision = router.route(
            first["prompt"],
            budget_tier="balanced",
            task_type=str(spec.get("task_type", first.get("task_type", ""))),
            difficulty=str(spec.get("difficulty", "")),
            risk_level=str(spec.get("risk_level", "")),
            evaluation_type=str(spec.get("evaluation_type", "")),
        )

        # Build candidate lookup from decision.candidates
        candidate_probs: dict[str, float] = {}
        for candidate in decision.candidates:
            mid = candidate.get("model_id", "")
            if mid in MODEL_ORDER:
                candidate_probs[mid] = candidate.get("pass_probability", 0.0)

        # For each model, record whether it "passes" (expected_min_model allows it)
        for model in MODEL_ORDER:
            from router_impls.geometric.features import MODEL_RANK

            # Ground truth: does this model pass for this prompt?
            if expected == "abstain":
                y_true_val = 0
            elif model in MODEL_RANK and expected in MODEL_RANK:
                y_true_val = 1 if MODEL_RANK[model] >= MODEL_RANK[expected] else 0
            else:
                y_true_val = 0

            y_score_val = candidate_probs.get(model, 0.0)

            model_scores[model]["y_true"].append(y_true_val)
            model_scores[model]["y_score"].append(y_score_val)

    # Compute ROC-AUC per model
    result: dict[str, Any] = {}
    for model in MODEL_ORDER:
        y_true = np.array(model_scores[model]["y_true"])
        y_score = np.array(model_scores[model]["y_score"])

        unique_classes = np.unique(y_true)
        if len(unique_classes) < 2:
            result[model] = None
        else:
            try:
                auc = float(roc_auc_score(y_true, y_score))
                result[model] = round(auc, 4)
            except ValueError:
                result[model] = None

    return result
