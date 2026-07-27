from __future__ import annotations

from pathlib import Path

import pandas as pd

from router_impls.geometric.features import MODEL_ORDER, MODEL_RANK


MODEL_COSTS = {
    "cheap": 0.01,
    "mid": 0.05,
    "premium": 0.20,
}


def build_weak_external_train_rows(specs_df: pd.DataFrame) -> pd.DataFrame:
    """Create model-level weak labels from external routing specs.

    External public datasets usually provide prompts, not three candidate model
    outputs for this challenge. This bridge keeps the data useful for routing by
    turning each expected_min_model label into deterministic quality targets.
    """

    rows = []
    for row in specs_df.fillna("").itertuples(index=False):
        prompt_id = str(getattr(row, "prompt_id", "")).strip()
        prompt = str(getattr(row, "prompt", "")).strip()
        expected = str(getattr(row, "expected_min_model", "") or "mid").strip().lower()
        if not prompt_id or not prompt:
            continue
        for model_id in MODEL_ORDER:
            rows.append(
                {
                    "prompt_id": prompt_id,
                    "prompt": prompt,
                    "model_id": model_id,
                    "model_output": weak_model_output(model_id, expected),
                    "quality_score": weak_quality_score(model_id, expected),
                    "cost": MODEL_COSTS[model_id],
                }
            )
    return pd.DataFrame(rows)


def weak_quality_score(model_id: str, expected_min_model: str) -> float:
    expected = expected_min_model if expected_min_model in MODEL_RANK else "mid"
    if expected_min_model == "abstain":
        return 0.20
    if MODEL_RANK[model_id] < MODEL_RANK[expected]:
        return 0.45 if model_id == "cheap" else 0.65
    if model_id == expected:
        return 0.90
    return 0.94


def weak_model_output(model_id: str, expected_min_model: str) -> str:
    if expected_min_model == "abstain":
        return "Insufficient context; abstain is recommended."
    if MODEL_RANK.get(model_id, -1) < MODEL_RANK.get(expected_min_model, 1):
        return "Weak external routing label: insufficient candidate."
    return "Weak external routing label: sufficient candidate."


def load_training_with_external(
    train_path: str | Path,
    specs_path: str | Path,
    external_specs_path: str | Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    train_df = pd.read_csv(train_path)
    specs_df = pd.read_csv(specs_path) if Path(specs_path).exists() else pd.DataFrame()
    summary = {
        "public_train_rows": int(len(train_df)),
        "public_spec_rows": int(len(specs_df)),
        "external_spec_rows": 0,
        "external_train_rows": 0,
        "combined_train_rows": int(len(train_df)),
        "combined_spec_rows": int(len(specs_df)),
    }
    if external_specs_path is None:
        return train_df, specs_df, summary

    external_path = Path(external_specs_path)
    if not external_path.exists():
        return train_df, specs_df, summary

    external_specs = pd.read_csv(external_path)
    external_train = build_weak_external_train_rows(external_specs)
    if external_specs.empty or external_train.empty:
        return train_df, specs_df, summary

    combined_train = pd.concat([train_df, external_train], ignore_index=True)
    combined_specs = pd.concat([specs_df, external_specs], ignore_index=True)
    summary.update(
        {
            "external_spec_rows": int(len(external_specs)),
            "external_train_rows": int(len(external_train)),
            "combined_train_rows": int(len(combined_train)),
            "combined_spec_rows": int(len(combined_specs)),
        }
    )
    return combined_train, combined_specs, summary
