from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from router_impls.geometric.features import MODEL_ORDER, MODEL_RANK


FEEDBACK_COLUMNS = {
    "prompt",
    "budget_tier",
    "selected_model_id",
    "was_wrong",
    "expected_model_id",
}
MODEL_COSTS = {"cheap": 0.01, "mid": 0.05, "premium": 0.20}


def load_feedback_rows(path: str | Path) -> pd.DataFrame:
    feedback_path = Path(path)
    if not feedback_path.exists() or feedback_path.stat().st_size == 0:
        return pd.DataFrame()
    df = pd.read_csv(feedback_path).fillna("")
    missing = FEEDBACK_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(f"feedback file missing columns: {sorted(missing)}")
    df = df[df["prompt"].astype(str).str.strip() != ""].copy()
    df = df[df["expected_model_id"].astype(str).isin([*MODEL_ORDER, "abstain"])].copy()
    df = df[df["was_wrong"].astype(str).str.lower().isin(["true", "1", "yes", "y"])].copy()
    return df.reset_index(drop=True)


def feedback_to_training_frames(
    feedback_df: pd.DataFrame,
    *,
    prompt_id_prefix: str = "fb",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if feedback_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    train_rows = []
    spec_rows = []
    for index, row in enumerate(feedback_df.itertuples(index=False), start=1):
        prompt = str(getattr(row, "prompt")).strip()
        expected_model = str(getattr(row, "expected_model_id")).strip()
        prompt_id = f"{prompt_id_prefix}{index:04d}"
        evaluation_type = "required_clarification" if expected_model == "abstain" else "rubric_check"
        difficulty = _difficulty_for_expected(expected_model)
        risk_level = "medium" if expected_model in {"premium", "abstain"} else "low"
        note = str(getattr(row, "user_note", "") or "")

        spec_rows.append(
            {
                "prompt_id": prompt_id,
                "prompt": prompt,
                "task_type": "feedback_route_correction",
                "difficulty": difficulty,
                "risk_level": risk_level,
                "expected_min_model": expected_model,
                "evaluation_type": evaluation_type,
                "reference_answer": "",
                "test_spec": json.dumps(
                    {
                        "source": "online_feedback",
                        "budget_tier": str(getattr(row, "budget_tier", "")),
                        "selected_model_id": str(getattr(row, "selected_model_id", "")),
                        "selection_reason": str(getattr(row, "selection_reason", "")),
                        "note": note,
                    },
                    ensure_ascii=False,
                ),
            }
        )

        for model_id in MODEL_ORDER:
            train_rows.append(
                {
                    "prompt_id": prompt_id,
                    "prompt": prompt,
                    "domain": "feedback",
                    "task_type": "feedback_route_correction",
                    "benchmark_id": "online_feedback",
                    "model_id": model_id,
                    "model_output": _feedback_model_output(model_id, expected_model),
                    "quality_score": _quality_for_model(model_id, expected_model),
                    "cost": MODEL_COSTS[model_id],
                }
            )

    return pd.DataFrame(train_rows), pd.DataFrame(spec_rows)


def merge_feedback_training(
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame,
    feedback_path: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    feedback_df = load_feedback_rows(feedback_path)
    feedback_train, feedback_specs = feedback_to_training_frames(feedback_df)
    summary = {
        "feedback_rows": int(len(feedback_df)),
        "feedback_train_rows": int(len(feedback_train)),
        "feedback_spec_rows": int(len(feedback_specs)),
        "feedback_path": str(feedback_path),
    }
    if feedback_train.empty:
        return train_df, specs_df, summary
    return (
        pd.concat([train_df, feedback_train], ignore_index=True),
        pd.concat([specs_df, feedback_specs], ignore_index=True),
        summary,
    )


def _difficulty_for_expected(expected_model: str) -> str:
    if expected_model == "cheap":
        return "easy"
    if expected_model == "mid":
        return "medium"
    return "hard"


def _quality_for_model(model_id: str, expected_model: str) -> float:
    if expected_model == "abstain":
        return 0.10
    if MODEL_RANK[model_id] >= MODEL_RANK[expected_model]:
        return 0.92
    return 0.35


def _feedback_model_output(model_id: str, expected_model: str) -> str:
    if expected_model == "abstain":
        return f"{model_id} should not answer without clarification."
    if MODEL_RANK[model_id] >= MODEL_RANK[expected_model]:
        return f"{model_id} sufficient feedback-aligned answer."
    return f"{model_id} insufficient feedback answer."
