from __future__ import annotations

import json
from dataclasses import dataclass

import pandas as pd

from geometric_router.features import MODEL_ORDER, MODEL_RANK


@dataclass(frozen=True)
class EvaluationResult:
    success: bool
    score: float
    reason: str


class OutputEvaluator:
    """Small deterministic evaluator for public sample outputs.

    The evaluator is intentionally conservative. When a task cannot be checked
    structurally, it falls back to the provided quality score instead of
    pretending that a keyword rubric is objective.
    """

    def __init__(self, fallback_threshold: float = 0.85):
        self.fallback_threshold = fallback_threshold

    def evaluate(self, output: str, spec: dict | None, quality_score: float | None = None) -> EvaluationResult:
        if not spec:
            return self._quality_fallback(quality_score, "quality_fallback_no_spec")

        evaluation_type = str(spec.get("evaluation_type", "")).strip()
        reference = "" if pd.isna(spec.get("reference_answer", "")) else str(spec.get("reference_answer", ""))

        if evaluation_type in {"exact_match", "numeric_count"}:
            success = str(output).strip() == reference
            return EvaluationResult(success, 1.0 if success else 0.0, evaluation_type)

        if evaluation_type == "exact_json":
            success = self._json_equal(output, reference)
            if success:
                return EvaluationResult(True, 1.0, "exact_json")
            return self._quality_fallback(quality_score, "exact_json_quality_fallback")

        if evaluation_type == "required_clarification":
            return self._quality_fallback(quality_score, "clarification_quality_fallback")

        if evaluation_type in {"unit_test", "constraint_check", "rubric_check"}:
            return self._quality_fallback(quality_score, f"{evaluation_type}_quality_fallback")

        return self._quality_fallback(quality_score, "unknown_eval_quality_fallback")

    def expected_success_from_min_model(self, model_id: str, expected_min_model: str) -> bool:
        if expected_min_model not in MODEL_RANK:
            return False
        return MODEL_RANK[model_id] >= MODEL_RANK[expected_min_model]

    def _quality_fallback(self, quality_score: float | None, reason: str) -> EvaluationResult:
        if quality_score is None:
            return EvaluationResult(False, 0.0, reason)
        score = float(quality_score)
        return EvaluationResult(score >= self.fallback_threshold, score, reason)

    def _json_equal(self, output: str, reference: str) -> bool:
        if not reference:
            return False
        try:
            return json.loads(output) == json.loads(reference)
        except Exception:
            return False


def build_training_labels(
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame | None,
    fallback_threshold: float = 0.85,
) -> pd.DataFrame:
    evaluator = OutputEvaluator(fallback_threshold=fallback_threshold)
    specs = {}
    if specs_df is not None and not specs_df.empty:
        specs = {row.prompt_id: row._asdict() for row in specs_df.itertuples(index=False)}

    rows = []
    for row in train_df.itertuples(index=False):
        spec = specs.get(row.prompt_id)
        result = evaluator.evaluate(row.model_output, spec, row.quality_score)
        rows.append(
            {
                "prompt_id": row.prompt_id,
                "model_id": row.model_id,
                "success": bool(result.success),
                "success_score": float(result.score),
                "success_reason": result.reason,
            }
        )

    labels = pd.DataFrame(rows)
    min_models = []
    for prompt_id, group in labels.groupby("prompt_id", sort=False):
        successful = [
            model
            for model in MODEL_ORDER
            if bool(group.loc[group["model_id"] == model, "success"].any())
        ]
        expected = successful[0] if successful else "premium"
        min_models.append({"prompt_id": prompt_id, "expected_min_model": expected})

    return labels.merge(pd.DataFrame(min_models), on="prompt_id", how="left")
