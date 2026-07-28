from __future__ import annotations

from pathlib import Path

import pandas as pd

from routing_stack.training.outcome_matrix import (
    build_outcome_matrix_from_training,
    load_outcome_matrix,
    outcome_matrix_to_training_frames,
)


DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "public"


def test_build_outcome_matrix_from_training_has_pairwise_gain_columns():
    train_df = pd.read_csv(DATA_DIR / "example_train.csv")
    specs_df = pd.read_csv(DATA_DIR / "example_eval_specs.csv")

    matrix = build_outcome_matrix_from_training(train_df, specs_df)

    assert "mid_gain_over_cheap" in matrix.columns
    assert "premium_gain_over_mid" in matrix.columns
    assert len(matrix) == train_df["prompt_id"].nunique()


def test_outcome_matrix_to_training_frames_converts_wide_rows():
    outcome = pd.DataFrame(
        [
            {
                "prompt_id": "o1",
                "prompt": "hello",
                "budget_tier": "balanced",
                "task_type": "chat",
                "difficulty": "easy",
                "risk_level": "low",
                "evaluation_type": "rubric_check",
                "cheap_output": "hi",
                "cheap_score": 0.8,
                "cheap_pass": True,
                "mid_output": "hello",
                "mid_score": 0.9,
                "mid_pass": True,
                "premium_output": "hello there",
                "premium_score": 0.91,
                "premium_pass": True,
                "min_sufficient_model": "cheap",
                "best_model": "premium",
                "premium_gain_over_mid": 0.01,
                "mid_gain_over_cheap": 0.1,
                "abstain_is_correct": False,
                "failure_reason": "",
            }
        ]
    )

    train_df, specs_df = outcome_matrix_to_training_frames(outcome)

    assert set(train_df["model_id"]) == {"cheap", "mid", "premium"}
    assert "reviewed_pass" in train_df.columns
    assert specs_df.iloc[0]["expected_min_model"] == "cheap"


def test_load_outcome_matrix_returns_empty_for_missing_path(tmp_path):
    loaded = load_outcome_matrix(tmp_path / "missing.csv")

    assert loaded.empty
