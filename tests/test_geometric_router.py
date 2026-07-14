from pathlib import Path

import pandas as pd

from geometric_router.evaluator import build_training_labels
from geometric_router.router import GeometricRouter


DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "public"


def load_data():
    train_df = pd.read_csv(DATA_DIR / "example_train.csv")
    specs_df = pd.read_csv(DATA_DIR / "example_eval_specs.csv")
    return train_df, specs_df


def test_training_labels_capture_exact_answer_failure():
    train_df, specs_df = load_data()
    labels = build_training_labels(train_df, specs_df)

    e001 = labels[labels["prompt_id"] == "e001"].set_index("model_id")
    assert bool(e001.loc["cheap", "success"]) is True
    assert bool(e001.loc["mid", "success"]) is True
    assert bool(e001.loc["premium", "success"]) is False
    assert e001.loc["cheap", "expected_min_model"] == "cheap"


def test_geometric_router_prefers_cheap_for_exact_prompt():
    train_df, specs_df = load_data()
    router = GeometricRouter.fit(train_df, specs_df)

    decision = router.route(
        "2 + 3의 값만 숫자로 답해줘.",
        budget_tier="balanced",
        task_type="math_exact",
        difficulty="trivial",
        risk_level="low",
        evaluation_type="exact_match",
    )

    assert decision.selected_model_id == "cheap"
    assert decision.selection_reason in {"cheapest_feasible_envelope", "nearest_envelope_fallback"}


def test_geometric_router_escalates_hard_architecture_prompt():
    train_df, specs_df = load_data()
    router = GeometricRouter.fit(train_df, specs_df)

    decision = router.route(
        "멀티테넌트 결제 시스템을 설계하고 웹훅 멱등성, 감사 로그, 장애 재처리, 보안 통제를 포함해줘.",
        budget_tier="fast",
        task_type="architecture_constraints",
        difficulty="hard",
        risk_level="high",
        evaluation_type="rubric_check",
    )

    assert decision.selected_model_id in {"mid", "premium"}


def test_geometric_router_save_and_load(tmp_path):
    train_df, specs_df = load_data()
    router = GeometricRouter.fit(train_df, specs_df)
    artifact = tmp_path / "router.json"
    router.save(artifact)

    loaded = GeometricRouter.load(artifact)
    decision = loaded.route("안녕", budget_tier="fast")

    assert decision.selected_model_id in {"cheap", "mid", "premium"}
    assert set(loaded.envelopes) == {"cheap", "mid", "premium"}
