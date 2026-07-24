from pathlib import Path
import json

import pandas as pd

from router_impls.geometric.evaluator import OutputEvaluator, build_training_labels
from router_impls.geometric.budget_allocator import allocate_public_budget
from router_impls.geometric.router import GeometricRouter
from router_impls.geometric.simulator import simulate_public_set
from router_impls.geometric.submission import RouterSubmission
from router_impls.geometric.task_classifier import TaskClassifier
from router_impls.geometric.tuning import tune_router_policy


DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "public"


def load_data():
    train_df = pd.read_csv(DATA_DIR / "example_train.csv")
    specs_df = pd.read_csv(DATA_DIR / "example_eval_specs.csv")
    return train_df, specs_df


def test_evaluator_runs_python_unit_tests():
    evaluator = OutputEvaluator()
    spec = {
        "evaluation_type": "unit_test",
        "test_spec": json.dumps(
            {
                "language": "python",
                "assertions": ["assert add(2,3)==5", "assert add(-1,1)==0"],
                "pass_threshold": 1.0,
            }
        ),
    }

    result = evaluator.evaluate("def add(a, b):\\n    return a + b", spec, quality_score=0.0)

    assert result.success is True
    assert result.reason == "unit_test_python"


def test_evaluator_compares_json_semantically_and_preserves_types():
    evaluator = OutputEvaluator()
    spec = {
        "evaluation_type": "exact_json",
        "reference_answer": '[{"name":"Kim","age":30}]',
        "test_spec": "parse_json_and_compare_types",
    }

    assert evaluator.evaluate('[{"age":30,"name":"Kim"}]', spec, quality_score=0.0).success is True
    assert evaluator.evaluate('[{"age":"30","name":"Kim"}]', spec, quality_score=1.0).success is False


def test_evaluator_checks_constraints_and_rubrics():
    evaluator = OutputEvaluator()
    constraint_spec = {
        "evaluation_type": "constraint_check",
        "test_spec": json.dumps({"bullet_count": 2, "required_terms": ["alpha", "beta"], "pass_threshold": 0.8}),
    }
    rubric_spec = {
        "evaluation_type": "rubric_check",
        "test_spec": json.dumps(
            {
                "required_concepts": ["tenant isolation", "idempotency key", "audit log"],
                "relations": [],
                "forbidden_claims": [],
                "critical_failures": [],
                "pass_threshold": 0.7,
            }
        ),
    }

    constraint = evaluator.evaluate("- alpha\n- beta", constraint_spec, quality_score=0.0)
    rubric = evaluator.evaluate(
        "Use tenant isolation, an idempotency key, and an audit log.",
        rubric_spec,
        quality_score=0.0,
    )

    assert constraint.success is True
    assert rubric.success is True


def test_evaluator_requires_clarification_instead_of_direct_answer():
    evaluator = OutputEvaluator()
    spec = {
        "evaluation_type": "required_clarification",
        "test_spec": json.dumps(
            {
                "required_requests": ["contract text", "jurisdiction"],
                "clarification_markers": ["cannot", "provide"],
                "forbidden_claims": ["valid."],
                "pass_threshold": 0.7,
            }
        ),
    }

    direct = evaluator.evaluate("It is valid.", spec, quality_score=1.0)
    clarification = evaluator.evaluate(
        "I cannot decide without the contract text and jurisdiction. Please provide them.",
        spec,
        quality_score=0.0,
    )

    assert direct.success is False
    assert clarification.success is True


def test_evaluator_checks_impossible_request_refusal():
    evaluator = OutputEvaluator()
    spec = {
        "evaluation_type": "refusal_check",
        "test_spec": json.dumps(
            {
                "required_claims": [{"any_of": ["불가능", "cannot"]}],
                "required_actions": [{"any_of": ["범위", "구체"]}],
                "forbidden_claims": ["모든 코드를 가져왔습니다"],
                "critical_failures": [],
                "pass_threshold": 0.8,
            },
            ensure_ascii=False,
        ),
    }

    bad = evaluator.evaluate("모든 코드를 가져왔습니다.", spec, quality_score=1.0)
    good = evaluator.evaluate("범위가 무한해서 불가능합니다. 구체적인 저장소나 언어를 알려주세요.", spec, quality_score=0.0)

    assert bad.success is False
    assert good.success is True


def test_geometric_router_can_abstain_for_impossible_request():
    train_df, specs_df = load_data()
    router = GeometricRouter.fit(train_df, specs_df)

    decision = router.route("이 세상 모든 코드를 가져와줘.", budget_tier="fast")

    assert decision.selected_model_id == "abstain"
    assert decision.selection_reason == "abstain_probability"


def test_task_classifier_predicts_independent_heads():
    _train_df, specs_df = load_data()
    classifier = TaskClassifier.fit(specs_df)

    impossible = classifier.predict("이 세상 모든 코드를 가져와줘.")
    exact = classifier.predict("2 + 3의 값만 숫자로 답해줘.")

    assert impossible["evaluation_type"] == "refusal_check"
    assert impossible["risk_level"] in {"medium", "high"}
    assert exact["evaluation_type"] in {"exact_match", "numeric_count", "numeric_check"}
    assert exact["difficulty"] == "trivial"
    assert "field_confidence" in impossible


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


def test_geometric_router_keeps_short_directive_on_cheap():
    train_df, specs_df = load_data()
    router = GeometricRouter.fit(train_df, specs_df)

    for tier in ["fast", "balanced", "premium"]:
        decision = router.route("이모티콘좀 그만 써라", budget_tier=tier)

        assert decision.selected_model_id == "cheap"
        assert decision.selection_reason == "simple_prompt_prior"
        assert decision.evidence["simple_prompt_prior"] == 1.0


def test_loaded_geometric_artifact_keeps_short_directive_on_cheap():
    artifact = Path(__file__).resolve().parents[3] / "artifacts" / "geometric_router.json"
    router = GeometricRouter.load(artifact)

    decision = router.route("이모티콘좀 그만 써라", budget_tier="fast")

    assert decision.selected_model_id == "cheap"
    assert decision.selection_reason == "simple_prompt_prior"


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


def test_fast_budget_guard_limits_inferred_premium_to_mid():
    train_df, specs_df = load_data()
    router = GeometricRouter.fit(train_df, specs_df)

    decision = router.route(
        "멀티테넌트 SaaS 결제 시스템의 상위 수준 아키텍처를 설계해줘.",
        budget_tier="fast",
        task_type="complex_design",
    )

    assert decision.selected_model_id == "mid"
    assert decision.evidence["explicit_task_context"] == 0.0


def test_fast_budget_guard_allows_explicit_high_risk_premium():
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

    assert decision.selected_model_id in {"premium", "mid"}
    assert decision.evidence["explicit_task_context"] == 1.0


def test_geometric_router_uses_request_model_metadata_costs():
    train_df, specs_df = load_data()
    router = GeometricRouter.fit(train_df, specs_df)

    decision = router.route(
        "2 + 3의 값만 숫자로 답해줘.",
        budget_tier="fast",
        task_type="math_exact",
        difficulty="trivial",
        risk_level="low",
        evaluation_type="exact_match",
        model_metadata=[
            {"model_id": "cheap", "cost": 0.02},
            {"model_id": "mid", "cost": 0.07},
            {"model_id": "premium", "cost": 0.30},
        ],
    )

    costs = {candidate["model_id"]: candidate["cost"] for candidate in decision.candidates}
    assert costs["cheap"] == 0.02
    assert costs["mid"] == 0.07
    assert costs["premium"] == 0.30
    assert decision.evidence["request_model_costs"] == {"cheap": 0.02, "mid": 0.07, "premium": 0.30}


def test_submission_selects_existing_history_output_when_sufficient(tmp_path):
    train_df, specs_df = load_data()
    artifact = tmp_path / "router.json"
    GeometricRouter.fit(train_df, specs_df).save(artifact)
    submission = RouterSubmission(artifact)

    payload = submission.route(
        prompt="2 + 3의 값만 숫자로 답해줘.",
        budget_tier="fast",
        history=[{"model_id": "cheap", "output": "5"}],
        model_metadata=[{"model_id": "cheap", "cost": 0.01}],
        task_type="math_exact",
        difficulty="trivial",
        risk_level="low",
        evaluation_type="exact_match",
    )

    assert payload["action"] == {"type": "select_output", "model_id": "cheap", "history_index": 0}


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


def test_budget_allocator_reports_tradeoff_against_online_fast_policy():
    train_df, specs_df = load_data()
    router = GeometricRouter.fit(train_df, specs_df)
    tune_router_policy(router, train_df, specs_df, tiers=("fast",))
    independent = simulate_public_set(router, train_df, specs_df, tiers=("fast",))["summary"]["tier_summary"]["fast"]
    payload = allocate_public_budget(router, train_df, specs_df, "fast")
    summary = payload["summary"]

    assert summary["total_cost"] <= summary["total_budget"]
    assert summary["mean_cost"] <= independent["mean_cost"]
    assert summary["under_route"] >= summary["under_route_lower_bound"]


