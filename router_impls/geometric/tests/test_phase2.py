from __future__ import annotations

import numpy as np

from router_impls.geometric.cross_validation import cross_validate_router
from router_impls.geometric.evaluator import build_training_labels
from router_impls.geometric.features import EvidenceExtractor
from router_impls.geometric.router import GeometricRouter
from router_impls.geometric.synthetic_data import smote_augment_features
from router_impls.geometric.tests.test_geometric_router import load_data, make_router


# -- Feature engineering tests --------------------------------------------------


def test_feature_vector_dimension_is_34():
    extractor = EvidenceExtractor()
    evidence = extractor.transform("테스트 프롬프트", difficulty="hard", risk_level="high")
    vec = evidence.as_vector()
    assert vec.shape[0] == 34


def test_interaction_features_are_products():
    extractor = EvidenceExtractor()
    evidence = extractor.transform(
        "코드를 작성하고 조건을 추가해줘",
        difficulty="hard",
        risk_level="high",
        evaluation_type="unit_test",
    )
    assert abs(evidence.difficulty_risk_interaction - evidence.difficulty_score * evidence.risk_score) < 1e-9
    assert abs(evidence.code_complexity_interaction - evidence.code_like * evidence.condition_count) < 1e-9
    assert abs(evidence.cost_pressure_interaction - evidence.token_count_norm * evidence.cost_estimate_norm) < 1e-9


def test_log_transform_compresses_token_features():
    extractor = EvidenceExtractor()
    short = extractor.transform("짧은 문장")
    long_text = "긴 문장입니다. " * 80
    long = extractor.transform(long_text)

    # Log-transformed token_count_norm should be > 0 for non-trivial prompts
    assert long.token_count_norm > short.token_count_norm
    # Log transform compresses: long prompt's norm should be < 1.0 for moderate lengths
    assert 0.0 < short.token_count_norm < 1.0
    assert 0.0 < long.token_count_norm <= 1.0


def test_interaction_features_in_explain():
    extractor = EvidenceExtractor()
    explained = extractor.explain("테스트", difficulty="hard", risk_level="high")
    assert "difficulty_risk_interaction" in explained
    assert "code_complexity_interaction" in explained
    assert "cost_pressure_interaction" in explained


# -- SMOTE augmentation tests ---------------------------------------------------


def test_smote_generates_minority_samples():
    train_df, specs_df = load_data()
    router = GeometricRouter.fit(train_df, specs_df, include_smote=False)

    # Extract features manually for SMOTE input
    extractor = EvidenceExtractor()
    labels = build_training_labels(train_df, specs_df)
    spec_map = {}
    if specs_df is not None:
        spec_map = {row.prompt_id: row._asdict() for row in specs_df.itertuples(index=False)}

    prompt_features = {}
    prompt_texts = {}
    for prompt_id, group in train_df.groupby("prompt_id", sort=False):
        first = group.iloc[0]
        spec = spec_map.get(prompt_id, {})
        evidence = extractor.transform(
            first["prompt"],
            task_type=str(spec.get("task_type", first.get("task_type", ""))),
            difficulty=str(spec.get("difficulty", "")),
            risk_level=str(spec.get("risk_level", "")),
            evaluation_type=str(spec.get("evaluation_type", "")),
        )
        prompt_features[prompt_id] = evidence.as_vector()
        prompt_texts[prompt_id] = str(first["prompt"])

    original_count = len(prompt_features)
    aug_features, aug_labels, aug_texts = smote_augment_features(
        prompt_features, labels, prompt_texts
    )

    assert len(aug_features) > original_count
    assert len(aug_labels) > len(labels)
    # Synthetic prompt IDs should start with "smote_"
    synthetic_ids = [pid for pid in aug_features if pid.startswith("smote_")]
    assert len(synthetic_ids) > 0


def test_smote_synthetic_labels_have_correct_structure():
    train_df, specs_df = load_data()
    labels = build_training_labels(train_df, specs_df)
    extractor = EvidenceExtractor()

    prompt_features = {}
    prompt_texts = {}
    for prompt_id, group in train_df.groupby("prompt_id", sort=False):
        first = group.iloc[0]
        evidence = extractor.transform(first["prompt"])
        prompt_features[prompt_id] = evidence.as_vector()
        prompt_texts[prompt_id] = str(first["prompt"])

    _, aug_labels, _ = smote_augment_features(prompt_features, labels, prompt_texts)

    synthetic_labels = aug_labels[aug_labels["prompt_id"].str.startswith("smote_")]
    if len(synthetic_labels) > 0:
        assert set(synthetic_labels.columns) == set(labels.columns)
        # Each synthetic prompt should have 3 model rows
        for pid in synthetic_labels["prompt_id"].unique():
            pid_rows = synthetic_labels[synthetic_labels["prompt_id"] == pid]
            assert set(pid_rows["model_id"]) == {"cheap", "mid", "premium"}


# -- Integration tests ----------------------------------------------------------


def test_router_fit_with_smote_enabled():
    train_df, specs_df = load_data()
    router = GeometricRouter.fit(train_df, specs_df, include_smote=True)

    decision = router.route("안녕하세요", budget_tier="fast")
    assert decision.selected_model_id in {"cheap", "mid", "premium", "abstain"}


def test_router_fit_with_smote_disabled():
    train_df, specs_df = load_data()
    router = GeometricRouter.fit(train_df, specs_df, include_smote=False)

    decision = router.route("안녕하세요", budget_tier="fast")
    assert decision.selected_model_id in {"cheap", "mid", "premium", "abstain"}


def test_cross_validation_works_with_new_features():
    train_df, specs_df = load_data()
    result = cross_validate_router(train_df, specs_df, n_folds=3)

    assert result.n_folds == 3
    assert len(result.fold_results) == 3
    agg = result.aggregated["overall_weighted_score"]
    assert agg["mean"] != 0.0


def test_router_still_routes_exact_answer_to_cheap():
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
