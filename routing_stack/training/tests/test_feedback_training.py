from __future__ import annotations

import pandas as pd

from routing_stack.training.feedback_training import (
    feedback_to_training_frames,
    load_feedback_rows,
    merge_feedback_training,
)


def test_feedback_to_training_frames_marks_expected_model_as_minimum():
    feedback = pd.DataFrame(
        [
            {
                "prompt": "이건 mid가 맞아",
                "budget_tier": "fast",
                "selected_model_id": "cheap",
                "selection_reason": "simple_prompt_prior",
                "was_wrong": "true",
                "expected_model_id": "mid",
                "user_note": "cheap 답변이 얕음",
            }
        ]
    )

    train_df, specs_df = feedback_to_training_frames(feedback)
    by_model = train_df.set_index("model_id")

    assert len(train_df) == 3
    assert specs_df.iloc[0]["expected_min_model"] == "mid"
    assert by_model.loc["cheap", "quality_score"] < 0.85
    assert by_model.loc["mid", "quality_score"] >= 0.85
    assert by_model.loc["premium", "quality_score"] >= 0.85


def test_load_feedback_rows_filters_non_wrong_and_invalid_expected(tmp_path):
    path = tmp_path / "feedback.csv"
    pd.DataFrame(
        [
            {
                "prompt": "keep",
                "budget_tier": "fast",
                "selected_model_id": "cheap",
                "was_wrong": "true",
                "expected_model_id": "premium",
            },
            {
                "prompt": "drop",
                "budget_tier": "fast",
                "selected_model_id": "cheap",
                "was_wrong": "false",
                "expected_model_id": "mid",
            },
            {
                "prompt": "drop-invalid",
                "budget_tier": "fast",
                "selected_model_id": "cheap",
                "was_wrong": "true",
                "expected_model_id": "unknown",
            },
        ]
    ).to_csv(path, index=False)

    loaded = load_feedback_rows(path)

    assert loaded["prompt"].tolist() == ["keep"]


def test_merge_feedback_training_appends_rows(tmp_path):
    feedback_path = tmp_path / "feedback.csv"
    pd.DataFrame(
        [
            {
                "prompt": "feedback prompt",
                "budget_tier": "balanced",
                "selected_model_id": "mid",
                "selection_reason": "nearest_budget_fallback",
                "was_wrong": "true",
                "expected_model_id": "premium",
                "user_note": "더 깊은 답 필요",
            }
        ]
    ).to_csv(feedback_path, index=False)
    train_df = pd.DataFrame(
        [
            {
                "prompt_id": "p1",
                "prompt": "base",
                "domain": "general",
                "task_type": "qa",
                "benchmark_id": "base",
                "model_id": "cheap",
                "model_output": "ok",
                "quality_score": 0.9,
                "cost": 0.01,
            }
        ]
    )
    specs_df = pd.DataFrame(
        [
            {
                "prompt_id": "p1",
                "prompt": "base",
                "task_type": "qa",
                "difficulty": "easy",
                "risk_level": "low",
                "expected_min_model": "cheap",
                "evaluation_type": "rubric_check",
                "reference_answer": "",
                "test_spec": "{}",
            }
        ]
    )

    merged_train, merged_specs, summary = merge_feedback_training(train_df, specs_df, feedback_path)

    assert len(merged_train) == 4
    assert len(merged_specs) == 2
    assert summary["feedback_rows"] == 1
    assert "fb0001" in set(merged_specs["prompt_id"])
