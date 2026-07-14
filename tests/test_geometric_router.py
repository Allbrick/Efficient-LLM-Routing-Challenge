from pathlib import Path

import pandas as pd

from geometric_router.evaluator import build_training_labels
from geometric_router.budget_allocator import allocate_public_budget
from geometric_router.router import GeometricRouter
from geometric_router.simulator import simulate_public_set
from geometric_router.tuning import tune_router_policy


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
    assert decision.selection_reason in {
        "cheapest_feasible_envelope",
        "nearest_envelope_fallback",
    }


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


def test_long_counting_prompt_is_cheap_on_fast():
    train_df, specs_df = load_data()
    router = GeometricRouter.fit(train_df, specs_df)
    paragraph = ("사과 바나나 포도 사과 귤사과 바나나 포도 사과 귤" * 60)

    decision = router.route(
        f'다음 문단에서 "사과"라는 단어가 몇 번 등장하는지만 알려주세요.\n\n{paragraph}',
        budget_tier="fast",
    )

    assert decision.evidence["exact_answer"] == 1.0
    assert decision.selected_model_id == "cheap"
    assert decision.selection_reason == "cheapest_feasible_envelope"


def test_geometric_router_save_and_load(tmp_path):
    train_df, specs_df = load_data()
    router = GeometricRouter.fit(train_df, specs_df)
    artifact = tmp_path / "router.json"
    router.save(artifact)

    loaded = GeometricRouter.load(artifact)
    decision = loaded.route("안녕", budget_tier="fast")

    assert decision.selected_model_id in {"cheap", "mid", "premium"}
    assert set(loaded.envelopes) == {"cheap", "mid", "premium"}


def test_simulator_reports_all_budget_tiers():
    train_df, specs_df = load_data()
    router = GeometricRouter.fit(train_df, specs_df)

    payload = simulate_public_set(router, train_df, specs_df)
    summary = payload["summary"]["tier_summary"]

    assert set(summary) == {"fast", "balanced", "premium"}
    assert summary["fast"]["count"] == train_df["prompt_id"].nunique()
    assert len(payload["rows"]) == train_df["prompt_id"].nunique() * 3


def test_policy_tuning_reduces_fast_budget_excess():
    train_df, specs_df = load_data()
    router = GeometricRouter.fit(train_df, specs_df)
    before = simulate_public_set(router, train_df, specs_df, tiers=("fast",))["summary"]["tier_summary"]["fast"]

    tune_router_policy(router, train_df, specs_df, tiers=("fast",))
    after = simulate_public_set(router, train_df, specs_df, tiers=("fast",))["summary"]["tier_summary"]["fast"]

    assert after["mean_excess_cost"] <= before["mean_excess_cost"]
    assert "fast" in router.radius_multipliers


def test_budget_allocator_respects_total_fast_budget():
    train_df, specs_df = load_data()
    router = GeometricRouter.fit(train_df, specs_df)
    payload = allocate_public_budget(router, train_df, specs_df, "fast")
    summary = payload["summary"]

    assert summary["total_cost"] <= summary["total_budget"]
    assert len(payload["rows"]) == train_df["prompt_id"].nunique()


def test_budget_allocator_uses_risk_model_to_reduce_fast_under_route():
    train_df, specs_df = load_data()
    router = GeometricRouter.fit(train_df, specs_df)
    tune_router_policy(router, train_df, specs_df, tiers=("fast",))
    independent = simulate_public_set(router, train_df, specs_df, tiers=("fast",))["summary"]["tier_summary"]["fast"]
    payload = allocate_public_budget(router, train_df, specs_df, "fast")
    summary = payload["summary"]

    assert summary["under_route"] <= independent["under_route"]
