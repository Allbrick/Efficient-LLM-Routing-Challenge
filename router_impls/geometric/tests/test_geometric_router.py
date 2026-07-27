from pathlib import Path
from copy import deepcopy
from functools import lru_cache
import json

import pandas as pd

from router_impls.geometric.evaluator import HeuristicRubricJudge, OutputEvaluator, build_training_labels
from router_impls.geometric.budget_allocator import allocate_public_budget
from router_impls.geometric.router import GeometricRouter
from router_impls.geometric.simulator import simulate_public_set
from router_impls.geometric.submission import RouterSubmission
from router_impls.geometric.task_classifier import TaskClassifier
from router_impls.geometric.tuning import score_tier_summary, tune_router_policy


DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "public"


@lru_cache(maxsize=1)
def load_data():
    train_df = pd.read_csv(DATA_DIR / "example_train.csv")
    specs_df = pd.read_csv(DATA_DIR / "example_eval_specs.csv")
    return train_df, specs_df


@lru_cache(maxsize=1)
def cached_router():
    train_df, specs_df = load_data()
    return GeometricRouter.fit(train_df, specs_df)


@lru_cache(maxsize=1)
def cached_semantic_router():
    train_df, specs_df = load_data()
    return GeometricRouter.fit(train_df, specs_df, use_semantic_features=True)


def make_router():
    return deepcopy(cached_router())


def make_semantic_router():
    return deepcopy(cached_semantic_router())


def sample_train_data(limit: int = 18):
    train_df, specs_df = load_data()
    prompt_ids = train_df["prompt_id"].drop_duplicates().head(limit)
    return train_df[train_df["prompt_id"].isin(prompt_ids)].copy(), specs_df


def test_geometric_router_stores_ood_reference_metadata():
    router = make_router()
    reference = router.metadata["ood_reference"]

    assert reference["score_high_threshold"] == 0.90
    assert reference["min_normalized_distance_p50"] <= reference["min_normalized_distance_p95"]


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


def test_evaluator_assesses_sufficiency_with_suggested_action():
    evaluator = OutputEvaluator()
    spec = {"evaluation_type": "exact_match", "reference_answer": "5"}

    sufficient = evaluator.assess_sufficiency("5", spec)
    insufficient = evaluator.assess_sufficiency("4", spec)

    assert sufficient.sufficient is True
    assert sufficient.suggested_action == "select_output"
    assert insufficient.sufficient is False
    assert insufficient.failure_reasons == ["exact_match"]
    assert insufficient.suggested_action == "escalate"


def test_optional_rubric_judge_can_assess_unstructured_rubric():
    evaluator = OutputEvaluator(rubric_judge=HeuristicRubricJudge())
    spec = {
        "evaluation_type": "rubric_check",
        "test_spec": json.dumps({"required_concepts": ["audit log", "idempotency"], "pass_threshold": 0.7}),
    }

    result = evaluator.assess_sufficiency(
        "The design includes an audit log and idempotency for retries.",
        spec,
        prompt="설계를 평가해줘",
    )

    assert result.sufficient is True
    assert result.suggested_action == "select_output"


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
    router = make_router()

    decision = router.route("이 세상 모든 코드를 가져와줘.", budget_tier="fast")

    assert decision.selected_model_id == "abstain"
    assert decision.selection_reason in {"abstain_probability", "missing_context_prior"}


def test_missing_context_lane_abstains_without_premium_call():
    router = make_router()

    decision = router.route("다음 코드를 고쳐줘", budget_tier="premium")

    assert decision.selected_model_id == "abstain"
    assert decision.selection_reason == "missing_context_prior"
    assert decision.evidence["pre_route_lane"] == "missing_context"
    assert decision.evidence["missing_context_lane"] == 1.0


def test_router_records_ood_and_uncertainty_scores():
    router = make_router()

    decision = router.route("🚀🚀🚀 unknown Ω≈ç√∫˜µ≤≥÷ prompt with rare symbols", budget_tier="fast")

    assert "ood_score" in decision.evidence
    assert "uncertainty_score" in decision.evidence
    assert 0.0 <= decision.evidence["ood_score"] <= 1.0
    assert 0.0 <= decision.evidence["uncertainty_score"] <= 1.0


def test_short_high_stakes_prompt_is_not_cheap_direct():
    router = make_router()

    decision = router.route("이 계약이 법적으로 유효한지 판단해줘", budget_tier="fast")

    assert decision.evidence["pre_route_lane"] in {"missing_context", "hard_task", "ambiguous"}
    assert decision.evidence["cheap_direct_lane"] == 0.0
    assert decision.evidence["high_stakes_domain"] == 1.0


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
    router = make_router()

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
        "exact_answer_prior",
        "cheapest_feasible_envelope",
        "nearest_envelope_fallback",
    }


def test_geometric_router_keeps_short_directive_on_cheap():
    train_df, specs_df = load_data()
    router = make_router()

    for tier in ["fast", "balanced", "premium"]:
        decision = router.route("이모티콘좀 그만 써라", budget_tier=tier)

        assert decision.selected_model_id == "cheap"
        assert decision.selection_reason == "simple_prompt_prior"
        assert decision.evidence["simple_prompt_prior"] == 1.0
        assert decision.evidence["pre_route_lane"] == "cheap_direct"


def test_loaded_geometric_artifact_keeps_short_directive_on_cheap():
    artifact = Path(__file__).resolve().parents[3] / "artifacts" / "geometric_router.json"
    router = GeometricRouter.load(artifact)

    decision = router.route("이모티콘좀 그만 써라", budget_tier="fast")

    assert decision.selected_model_id == "cheap"
    assert decision.selection_reason == "simple_prompt_prior"


def test_repeated_simple_prompt_stays_on_cheap():
    router = make_router()
    unit = "원피스 세계관에 대해 철학적 물음을 던져줘"
    repeated = unit * 15

    short_decision = router.route(unit, budget_tier="fast")
    repeated_decision = router.route(repeated, budget_tier="fast")

    assert short_decision.selected_model_id == "cheap"
    assert repeated_decision.selected_model_id == "cheap"
    assert repeated_decision.selection_reason == "repetition_normalized_prior"
    assert repeated_decision.evidence["repetition_ratio"] > 0.8
    assert repeated_decision.evidence["compressed_length_norm"] < repeated_decision.evidence["length_norm"] or repeated_decision.evidence["compressed_length_norm"] < 0.2


def test_long_non_repetitive_architecture_prompt_still_escalates():
    router = make_router()
    prompt = (
        "멀티테넌트 결제 시스템을 설계하고 웹훅 멱등성, 감사 로그, 장애 재처리, "
        "보안 통제, 데이터 격리, 장애 복구, 월말 정산, 권한 관리, 모니터링까지 포함해줘."
    )

    decision = router.route(prompt, budget_tier="fast")

    assert decision.selected_model_id in {"mid", "premium"}
    assert decision.evidence["repetition_ratio"] < 0.2


def test_geometric_router_escalates_hard_architecture_prompt():
    train_df, specs_df = load_data()
    router = make_router()

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
    router = make_router()

    decision = router.route(
        "멀티테넌트 SaaS 결제 시스템의 상위 수준 아키텍처를 설계해줘.",
        budget_tier="fast",
        task_type="complex_design",
    )

    assert decision.selected_model_id == "mid"
    assert decision.evidence["explicit_task_context"] == 0.0


def test_fast_budget_guard_allows_explicit_high_risk_premium():
    train_df, specs_df = load_data()
    router = make_router()

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
    router = make_router()

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
    make_router().save(artifact)
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


def test_submission_evaluates_history_before_selecting_output(tmp_path):
    train_df, specs_df = load_data()
    artifact = tmp_path / "router.json"
    make_router().save(artifact)
    submission = RouterSubmission(artifact)

    payload = submission.route(
        prompt="2 + 3의 값만 숫자로 답해줘.",
        budget_tier="fast",
        history=[{"model_id": "cheap", "output": "4"}, {"model_id": "mid", "output": "5"}],
        task_type="math_exact",
        difficulty="trivial",
        risk_level="low",
        evaluation_type="exact_match",
        reference_answer="5",
    )

    assert payload["action"] == {"type": "select_output", "model_id": "mid", "history_index": 1}


def test_submission_calls_model_when_structured_history_fails(tmp_path):
    train_df, specs_df = load_data()
    artifact = tmp_path / "router.json"
    make_router().save(artifact)
    submission = RouterSubmission(artifact)

    payload = submission.route(
        prompt="2 + 3의 값만 숫자로 답해줘.",
        budget_tier="fast",
        history=[{"model_id": "cheap", "output": "4"}],
        task_type="math_exact",
        difficulty="trivial",
        risk_level="low",
        evaluation_type="exact_match",
        reference_answer="5",
    )

    assert payload["action"] == {"type": "call_model", "model_id": "mid"}


def test_submission_selects_lower_rank_history_when_output_is_sufficient(tmp_path):
    artifact = tmp_path / "router.json"
    make_router().save(artifact)
    submission = RouterSubmission(artifact)

    payload = submission.route(
        prompt="2 + 3의 값만 숫자로 답해줘.",
        budget_tier="premium",
        history=[{"model_id": "cheap", "output": "5"}],
        task_type="math_exact",
        difficulty="hard",
        risk_level="high",
        evaluation_type="exact_match",
        reference_answer="5",
    )

    assert payload["action"] == {"type": "select_output", "model_id": "cheap", "history_index": 0}


def test_long_counting_prompt_is_cheap_on_fast():
    train_df, specs_df = load_data()
    router = make_router()
    paragraph = ("사과 바나나 포도 사과 귤사과 바나나 포도 사과 귤" * 60)

    decision = router.route(
        f'다음 문단에서 "사과"라는 단어가 몇 번 등장하는지만 알려주세요.\n\n{paragraph}',
        budget_tier="fast",
    )

    assert decision.evidence["exact_answer"] == 1.0
    assert decision.selected_model_id == "cheap"
    assert decision.selection_reason in {"exact_answer_prior", "cheapest_feasible_envelope", "low_complexity_prior"}


def test_geometric_router_save_and_load(tmp_path):
    train_df, specs_df = load_data()
    router = make_router()
    artifact = tmp_path / "router.json"
    router.save(artifact)

    loaded = GeometricRouter.load(artifact)
    decision = loaded.route("안녕", budget_tier="fast")

    assert decision.selected_model_id in {"cheap", "mid", "premium"}
    assert set(loaded.envelopes) == {"cheap", "mid", "premium"}


def test_geometric_router_can_use_optional_semantic_features(tmp_path):
    train_df, specs_df = load_data()
    router = make_semantic_router()

    decision = router.route("결제 시스템의 장애 복구 설계를 해줘.", budget_tier="balanced")

    assert router.semantic_index is not None
    assert "semantic_uncertainty" in decision.evidence
    artifact = tmp_path / "semantic_router.json"
    router.save(artifact)
    loaded = GeometricRouter.load(artifact)

    loaded_decision = loaded.route("결제 시스템의 장애 복구 설계를 해줘.", budget_tier="balanced")

    assert loaded.semantic_index is not None
    assert "nearest_premium_distance" in loaded_decision.evidence


def test_simulator_reports_all_budget_tiers():
    train_df, specs_df = load_data()
    router = make_router()

    payload = simulate_public_set(router, train_df, specs_df)
    summary = payload["summary"]["tier_summary"]

    assert set(summary) == {"fast", "balanced", "premium"}
    assert summary["fast"]["count"] == train_df["prompt_id"].nunique()
    assert len(payload["rows"]) == train_df["prompt_id"].nunique() * 3


def test_policy_tuning_reduces_fast_budget_excess():
    train_df, specs_df = load_data()
    router = make_router()
    before = simulate_public_set(router, train_df, specs_df, tiers=("fast",))["summary"]["tier_summary"]["fast"]

    tune_router_policy(router, train_df, specs_df, tiers=("fast",))
    after = simulate_public_set(router, train_df, specs_df, tiers=("fast",))["summary"]["tier_summary"]["fast"]

    assert after["mean_excess_cost"] <= before["mean_excess_cost"]
    assert "fast" in router.radius_multipliers


def test_policy_tuning_records_weighted_objective():
    train_df, specs_df = load_data()
    router = make_router()

    results = tune_router_policy(router, train_df, specs_df, tiers=("fast", "balanced"))

    assert "weighted_score" in results["fast"]
    assert "objective" in results["fast"]
    assert "under_route" in results["fast"]["objective"]["penalties"]
    assert "policy_objective" in router.metadata
    assert isinstance(router.metadata["policy_objective"]["overall_score"], float)


def test_score_tier_summary_penalizes_cost_overflow_and_under_route():
    good = {
        "count": 10,
        "mean_quality": 0.90,
        "mean_cost": 0.02,
        "mean_excess_cost": 0.0,
        "under_route": 0,
        "over_route": 1,
        "should_abstain": 0,
    }
    bad = {
        **good,
        "mean_cost": 0.08,
        "mean_excess_cost": 0.05,
        "under_route": 3,
    }

    assert score_tier_summary(good, "fast")["weighted_score"] > score_tier_summary(bad, "fast")["weighted_score"]


def test_budget_allocator_respects_total_fast_budget():
    train_df, specs_df = sample_train_data()
    router = GeometricRouter.fit(train_df, specs_df)
    payload = allocate_public_budget(router, train_df, specs_df, "fast")
    summary = payload["summary"]

    assert summary["total_cost"] <= summary["total_budget"]
    assert len(payload["rows"]) == train_df["prompt_id"].nunique()


def test_budget_allocator_reports_tradeoff_against_online_fast_policy():
    train_df, specs_df = sample_train_data()
    router = GeometricRouter.fit(train_df, specs_df)
    tune_router_policy(router, train_df, specs_df, tiers=("fast",))
    independent = simulate_public_set(router, train_df, specs_df, tiers=("fast",))["summary"]["tier_summary"]["fast"]
    payload = allocate_public_budget(router, train_df, specs_df, "fast")
    summary = payload["summary"]

    assert summary["total_cost"] <= summary["total_budget"]
    assert summary["mean_cost"] <= independent["mean_cost"]
    assert summary["under_route"] >= summary["under_route_lower_bound"]




