from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

from routing_stack.training.outcome_matrix import OUTCOME_COLUMNS


MODEL_SLOTS = ("cheap", "mid", "premium")
_PROMPT_ID_RE = re.compile(r"^r(\d+)$")


def next_prompt_id(path: str | Path, prefix: str = "r") -> str:
    matrix_path = Path(path)
    if not matrix_path.exists() or matrix_path.stat().st_size == 0:
        return f"{prefix}001"

    max_id = 0
    with matrix_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            match = _PROMPT_ID_RE.match(str(row.get("prompt_id", "")).strip())
            if match:
                max_id = max(max_id, int(match.group(1)))
    return f"{prefix}{max_id + 1:03d}"


def default_review_values(best_model: str) -> dict[str, Any]:
    _validate_model(best_model)
    values: dict[str, Any] = {}
    for model_id in MODEL_SLOTS:
        if model_id == best_model:
            values[f"{model_id}_score"] = 1.0
            values[f"{model_id}_pass"] = True
        elif _rank(model_id) > _rank(best_model):
            values[f"{model_id}_score"] = 0.9
            values[f"{model_id}_pass"] = True
        else:
            values[f"{model_id}_score"] = 0.55 if model_id == "mid" else 0.35
            values[f"{model_id}_pass"] = False
    values["min_sufficient_model"] = best_model
    values["best_model"] = best_model
    values["mid_gain_over_cheap"] = round(float(values["mid_score"]) - float(values["cheap_score"]), 4)
    values["premium_gain_over_mid"] = round(float(values["premium_score"]) - float(values["mid_score"]), 4)
    values["abstain_is_correct"] = False
    return values


def build_reviewed_outcome_row(
    *,
    path: str | Path,
    prompt: str,
    outputs: dict[str, str],
    best_model: str,
    metadata: dict[str, Any] | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prompt_text = prompt.strip()
    if not prompt_text:
        raise ValueError("prompt is required")
    _validate_model(best_model)

    row = {column: "" for column in OUTCOME_COLUMNS}
    row["prompt_id"] = next_prompt_id(path)
    row["prompt"] = prompt_text
    row.update(
        {
            "budget_tier": "balanced",
            "task_type": "manual_review",
            "difficulty": "",
            "risk_level": "",
            "evaluation_type": "human_preference",
            "failure_reason": "",
        }
    )
    if metadata:
        for key in ("budget_tier", "task_type", "difficulty", "risk_level", "evaluation_type", "failure_reason"):
            if key in metadata:
                row[key] = metadata[key]

    for model_id in MODEL_SLOTS:
        row[f"{model_id}_output"] = outputs.get(model_id, "")

    row.update(default_review_values(best_model))
    if overrides:
        for key, value in overrides.items():
            if key in OUTCOME_COLUMNS:
                row[key] = value

    _normalize_review_row(row)
    return row


def append_reviewed_outcome(path: str | Path, row: dict[str, Any]) -> Path:
    matrix_path = Path(path)
    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not matrix_path.exists() or matrix_path.stat().st_size == 0

    clean_row = {column: row.get(column, "") for column in OUTCOME_COLUMNS}
    _normalize_review_row(clean_row)
    with matrix_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(OUTCOME_COLUMNS))
        if write_header:
            writer.writeheader()
        writer.writerow(clean_row)
    return matrix_path


def _normalize_review_row(row: dict[str, Any]) -> None:
    for model_id in MODEL_SLOTS:
        score_key = f"{model_id}_score"
        pass_key = f"{model_id}_pass"
        row[score_key] = _as_float(row.get(score_key, 0.0))
        row[pass_key] = _as_bool(row.get(pass_key, False))

    if not row.get("min_sufficient_model"):
        for model_id in MODEL_SLOTS:
            if row[f"{model_id}_pass"]:
                row["min_sufficient_model"] = model_id
                break
        else:
            row["min_sufficient_model"] = "premium"

    row["mid_gain_over_cheap"] = round(float(row["mid_score"]) - float(row["cheap_score"]), 4)
    row["premium_gain_over_mid"] = round(float(row["premium_score"]) - float(row["mid_score"]), 4)
    row["abstain_is_correct"] = _as_bool(row.get("abstain_is_correct", False))


def _rank(model_id: str) -> int:
    return MODEL_SLOTS.index(model_id)


def _validate_model(model_id: str) -> None:
    if model_id not in MODEL_SLOTS:
        raise ValueError(f"unknown model slot: {model_id}")


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "pass", "passed"}


def _as_float(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, score))
