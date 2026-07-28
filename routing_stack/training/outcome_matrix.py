from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from router_impls.geometric.evaluator import build_training_labels
from router_impls.geometric.features import MODEL_ORDER, MODEL_RANK


OUTCOME_COLUMNS = (
    "prompt_id",
    "prompt",
    "budget_tier",
    "task_type",
    "difficulty",
    "risk_level",
    "evaluation_type",
    "cheap_output",
    "cheap_score",
    "cheap_pass",
    "mid_output",
    "mid_score",
    "mid_pass",
    "premium_output",
    "premium_score",
    "premium_pass",
    "min_sufficient_model",
    "best_model",
    "premium_gain_over_mid",
    "mid_gain_over_cheap",
    "abstain_is_correct",
    "failure_reason",
)

DEFAULT_MODEL_COSTS = {
    "cheap": 0.01,
    "mid": 0.05,
    "premium": 0.20,
}


def load_outcome_matrix(path: str | Path) -> pd.DataFrame:
    matrix_path = Path(path)
    if not matrix_path.exists() or matrix_path.stat().st_size == 0:
        return pd.DataFrame(columns=OUTCOME_COLUMNS)
    df = pd.read_csv(matrix_path).fillna("")
    missing = [column for column in OUTCOME_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"outcome matrix missing columns: {missing}")
    return df.loc[:, OUTCOME_COLUMNS].copy()


def outcome_matrix_to_training_frames(outcome_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if outcome_df.empty:
        return _empty_train_frame(), _empty_specs_frame()

    train_rows: list[dict[str, Any]] = []
    spec_rows: list[dict[str, Any]] = []
    for row in outcome_df.fillna("").itertuples(index=False):
        prompt_id = str(row.prompt_id)
        prompt = str(row.prompt)
        expected = _normalize_expected_model(str(row.min_sufficient_model), row)
        spec_rows.append(
            {
                "prompt_id": prompt_id,
                "prompt": prompt,
                "task_type": str(row.task_type),
                "difficulty": str(row.difficulty),
                "risk_level": str(row.risk_level),
                "expected_min_model": expected,
                "evaluation_type": str(row.evaluation_type),
                "reference_answer": "",
                "test_spec": "",
            }
        )
        for model_id in MODEL_ORDER:
            train_rows.append(
                {
                    "prompt_id": prompt_id,
                    "prompt": prompt,
                    "domain": "outcome_matrix",
                    "task_type": str(row.task_type),
                    "benchmark_id": "router_outcome_matrix",
                    "model_id": model_id,
                    "model_output": str(getattr(row, f"{model_id}_output")),
                    "quality_score": _quality_from_pass_or_score(
                        getattr(row, f"{model_id}_score"),
                        getattr(row, f"{model_id}_pass"),
                    ),
                    "reviewed_pass": _as_bool(getattr(row, f"{model_id}_pass")),
                    "cost": DEFAULT_MODEL_COSTS[model_id],
                }
            )
    return pd.DataFrame(train_rows), pd.DataFrame(spec_rows)


def merge_outcome_training(
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame,
    outcome_path: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    outcome_df = load_outcome_matrix(outcome_path)
    outcome_train, outcome_specs = outcome_matrix_to_training_frames(outcome_df)
    summary = {
        "outcome_matrix_path": str(outcome_path),
        "outcome_prompt_rows": int(len(outcome_df)),
        "outcome_train_rows": int(len(outcome_train)),
        "outcome_spec_rows": int(len(outcome_specs)),
    }
    if outcome_train.empty:
        return train_df, specs_df, summary
    return (
        pd.concat([train_df, outcome_train], ignore_index=True),
        pd.concat([specs_df, outcome_specs], ignore_index=True),
        summary,
    )


def build_outcome_matrix_from_training(
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame | None = None,
    fallback_threshold: float = 0.85,
) -> pd.DataFrame:
    labels = build_training_labels(train_df, specs_df, fallback_threshold=fallback_threshold)
    label_map = labels.set_index(["prompt_id", "model_id"]).to_dict(orient="index")
    specs = {}
    if specs_df is not None and not specs_df.empty:
        specs = {row.prompt_id: row._asdict() for row in specs_df.itertuples(index=False)}

    rows = []
    for prompt_id, group in train_df.groupby("prompt_id", sort=False):
        first = group.iloc[0]
        spec = specs.get(prompt_id, {})
        row: dict[str, Any] = {
            "prompt_id": prompt_id,
            "prompt": str(first["prompt"]),
            "budget_tier": "",
            "task_type": str(spec.get("task_type", first.get("task_type", ""))),
            "difficulty": str(spec.get("difficulty", "")),
            "risk_level": str(spec.get("risk_level", "")),
            "evaluation_type": str(spec.get("evaluation_type", "")),
            "min_sufficient_model": _min_sufficient_model(prompt_id, labels),
            "best_model": _best_model(group),
            "abstain_is_correct": _min_sufficient_model(prompt_id, labels) == "abstain",
            "failure_reason": "",
        }
        for model_id in MODEL_ORDER:
            model_row = group[group["model_id"] == model_id]
            label = label_map.get((prompt_id, model_id), {})
            if model_row.empty:
                row[f"{model_id}_output"] = ""
                row[f"{model_id}_score"] = 0.0
                row[f"{model_id}_pass"] = False
                continue
            item = model_row.iloc[0]
            row[f"{model_id}_output"] = str(item["model_output"])
            row[f"{model_id}_score"] = float(item["quality_score"])
            row[f"{model_id}_pass"] = bool(label.get("success", False))
        row["mid_gain_over_cheap"] = float(row["mid_score"]) - float(row["cheap_score"])
        row["premium_gain_over_mid"] = float(row["premium_score"]) - float(row["mid_score"])
        rows.append(row)
    return pd.DataFrame(rows, columns=OUTCOME_COLUMNS)


def _empty_train_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "prompt_id",
            "prompt",
            "domain",
            "task_type",
            "benchmark_id",
            "model_id",
            "model_output",
            "quality_score",
            "reviewed_pass",
            "cost",
        ]
    )


def _empty_specs_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "prompt_id",
            "prompt",
            "task_type",
            "difficulty",
            "risk_level",
            "expected_min_model",
            "evaluation_type",
            "reference_answer",
            "test_spec",
        ]
    )


def _normalize_expected_model(value: str, row: object) -> str:
    if value in MODEL_RANK or value == "abstain":
        return value
    for model_id in MODEL_ORDER:
        if _as_bool(getattr(row, f"{model_id}_pass")):
            return model_id
    return "premium"


def _quality_from_pass_or_score(score: object, passed: object) -> float:
    try:
        return float(score)
    except (TypeError, ValueError):
        return 1.0 if _as_bool(passed) else 0.0


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "pass", "passed"}


def _min_sufficient_model(prompt_id: str, labels: pd.DataFrame) -> str:
    group = labels[labels["prompt_id"] == prompt_id]
    if group.empty:
        return "premium"
    expected = str(group.iloc[0].get("expected_min_model", ""))
    return expected if expected else "premium"


def _best_model(group: pd.DataFrame) -> str:
    best = group.sort_values(["quality_score", "cost"], ascending=[False, True], kind="stable").iloc[0]
    return str(best["model_id"])
