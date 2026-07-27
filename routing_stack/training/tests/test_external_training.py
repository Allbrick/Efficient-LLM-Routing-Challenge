import pandas as pd

from routing_stack.training.external_training import (
    build_weak_external_train_rows,
    load_training_with_external,
    weak_quality_score,
)


def test_build_weak_external_train_rows_creates_three_model_rows():
    specs = pd.DataFrame(
        [
            {
                "prompt_id": "ext-1",
                "prompt": "Design a payment architecture.",
                "expected_min_model": "premium",
            }
        ]
    )

    rows = build_weak_external_train_rows(specs)

    assert len(rows) == 3
    assert set(rows["model_id"]) == {"cheap", "mid", "premium"}
    assert rows.loc[rows["model_id"] == "premium", "quality_score"].iloc[0] >= 0.85
    assert rows.loc[rows["model_id"] == "cheap", "quality_score"].iloc[0] < 0.85


def test_weak_quality_score_marks_abstain_models_as_low_quality():
    assert weak_quality_score("premium", "abstain") < 0.85


def test_load_training_with_external_merges_specs_and_train_rows(tmp_path):
    train_path = tmp_path / "train.csv"
    specs_path = tmp_path / "specs.csv"
    external_path = tmp_path / "external_specs.csv"
    pd.DataFrame(
        [
            {
                "prompt_id": "p1",
                "prompt": "2 + 3?",
                "model_id": "cheap",
                "model_output": "5",
                "quality_score": 1.0,
                "cost": 0.01,
            }
        ]
    ).to_csv(train_path, index=False)
    pd.DataFrame(
        [
            {
                "prompt_id": "p1",
                "prompt": "2 + 3?",
                "task_type": "math",
                "difficulty": "trivial",
                "risk_level": "low",
                "expected_min_model": "cheap",
                "evaluation_type": "exact_match",
                "reference_answer": "5",
                "test_spec": "",
            }
        ]
    ).to_csv(specs_path, index=False)
    pd.DataFrame(
        [
            {
                "prompt_id": "ext-1",
                "prompt": "Implement a queue.",
                "task_type": "code",
                "difficulty": "medium",
                "risk_level": "low",
                "expected_min_model": "mid",
                "evaluation_type": "unit_test",
                "reference_answer": "",
                "test_spec": "{}",
            }
        ]
    ).to_csv(external_path, index=False)

    train, specs, summary = load_training_with_external(train_path, specs_path, external_path)

    assert len(train) == 4
    assert len(specs) == 2
    assert summary["external_spec_rows"] == 1
    assert summary["external_train_rows"] == 3
