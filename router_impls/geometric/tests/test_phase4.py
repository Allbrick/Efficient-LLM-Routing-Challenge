from __future__ import annotations

import json

import numpy as np

from router_impls.geometric.features import MODEL_ORDER, EvidenceExtractor
from router_impls.geometric.logistic_pass_model import (
    LogisticPassModel,
    fit_logistic_pass_model,
)
from router_impls.geometric.risk_model import (
    PCATransform,
    SufficiencyRiskModel,
    fit_pca_transform,
    fit_risk_model,
)
from router_impls.geometric.router import GeometricRouter
from router_impls.geometric.tests.test_geometric_router import load_data, make_router
from router_impls.geometric.xai import (
    EVIDENCE_FEATURE_NAMES,
    contributions_to_evidence,
    decompose_all_models,
    decompose_mahalanobis,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_features_and_labels():
    from router_impls.geometric.evaluator import build_training_labels

    train_df, specs_df = load_data()
    labels = build_training_labels(train_df, specs_df)
    extractor = EvidenceExtractor()
    prompt_features = {}
    prompt_texts = {}
    for prompt_id, group in train_df.groupby("prompt_id", sort=False):
        first = group.iloc[0]
        prompt_texts[str(prompt_id)] = str(first["prompt"])
        evidence = extractor.transform(str(first["prompt"]))
        prompt_features[str(prompt_id)] = evidence.as_vector()
    return prompt_features, labels, prompt_texts


# ---------------------------------------------------------------------------
# Logistic Model Tests (3)
# ---------------------------------------------------------------------------


def test_logistic_pass_model_fit_and_predict():
    prompt_features, labels, _ = _build_features_and_labels()
    model = fit_logistic_pass_model(prompt_features, labels)
    x = next(iter(prompt_features.values()))
    predictions = model.predict_all(x)
    assert set(predictions.keys()) == set(MODEL_ORDER)
    for prob in predictions.values():
        assert 0.0 <= prob <= 1.0


def test_logistic_pass_model_serialization_round_trip():
    prompt_features, labels, _ = _build_features_and_labels()
    model = fit_logistic_pass_model(prompt_features, labels)
    payload = model.to_dict()
    restored = LogisticPassModel.from_dict(payload)
    x = next(iter(prompt_features.values()))
    orig_preds = model.predict_all(x)
    restored_preds = restored.predict_all(x)
    for mid in MODEL_ORDER:
        assert abs(orig_preds[mid] - restored_preds[mid]) < 1e-9


def test_logistic_coefficients_provide_feature_importance():
    prompt_features, labels, _ = _build_features_and_labels()
    model = fit_logistic_pass_model(prompt_features, labels)
    has_nonzero = False
    for mid, coeffs in model.models.items():
        if any(abs(c) > 1e-10 for c in coeffs.coefficients):
            has_nonzero = True
            break
    assert has_nonzero, "At least one model should have non-zero coefficients"


# ---------------------------------------------------------------------------
# PCA Tests (3)
# ---------------------------------------------------------------------------


def test_pca_reduces_risk_vector_dimension():
    prompt_features, labels, prompt_texts = _build_features_and_labels()
    risk_model = fit_risk_model(
        prompt_features, labels, prompt_texts, use_pca=True, pca_variance=0.90
    )
    assert risk_model.pca_transform is not None
    original_dim = len(risk_model.pca_transform.mean)
    reduced_dim = risk_model.pca_transform.n_components
    assert reduced_dim < original_dim
    total_var = sum(risk_model.pca_transform.explained_variance_ratio)
    assert total_var >= 0.90


def test_pca_transform_serialization_round_trip():
    rng = np.random.RandomState(42)
    vectors = rng.randn(50, 20)
    pca = fit_pca_transform(vectors, variance_threshold=0.90)
    payload = pca.to_dict()
    restored = PCATransform.from_dict(payload)
    x = rng.randn(20)
    orig = pca.transform(x)
    rest = restored.transform(x)
    np.testing.assert_allclose(orig, rest, atol=1e-10)


def test_risk_model_with_pca_produces_valid_distribution():
    prompt_features, labels, prompt_texts = _build_features_and_labels()
    risk_model = fit_risk_model(
        prompt_features, labels, prompt_texts, use_pca=True, pca_variance=0.90
    )
    x = next(iter(prompt_features.values()))
    dist = risk_model.predict_expected_distribution(x, "test prompt")
    total = sum(dist.values())
    assert abs(total - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# XAI Tests (4)
# ---------------------------------------------------------------------------


def test_xai_decomposition_sums_to_distance_squared():
    router = make_router()
    extractor = EvidenceExtractor()
    evidence = extractor.transform("테스트 프롬프트입니다")
    x = evidence.as_vector()
    envelope = router.envelopes["cheap"]
    fc = decompose_mahalanobis(x, envelope, EVIDENCE_FEATURE_NAMES)
    sum_contributions = sum(fc.contributions.values())
    assert abs(sum_contributions - fc.total_distance_squared) < 1e-6


def test_xai_decompose_all_models_covers_all_envelopes():
    router = make_router()
    extractor = EvidenceExtractor()
    evidence = extractor.transform("테스트 프롬프트입니다")
    x = evidence.as_vector()
    results = decompose_all_models(x, router.envelopes, EVIDENCE_FEATURE_NAMES)
    assert set(results.keys()) == set(MODEL_ORDER)


def test_xai_contributions_to_evidence_is_flat_dict():
    router = make_router()
    extractor = EvidenceExtractor()
    evidence = extractor.transform("테스트 프롬프트입니다")
    x = evidence.as_vector()
    results = decompose_all_models(x, router.envelopes, EVIDENCE_FEATURE_NAMES)
    flat = contributions_to_evidence(results)
    assert isinstance(flat, dict)
    for key, value in flat.items():
        assert isinstance(key, str)
        assert isinstance(value, float)


def test_route_decision_includes_feature_contributions():
    router = make_router()
    decision = router.route("테스트 프롬프트입니다", budget_tier="balanced")
    assert "feature_contributions" in decision.evidence
    contributions = decision.evidence["feature_contributions"]
    for mid in MODEL_ORDER:
        assert mid in contributions
        assert "total_distance" in contributions[mid]
        assert "top_pushing_away" in contributions[mid]


# ---------------------------------------------------------------------------
# Ensemble Tests (2)
# ---------------------------------------------------------------------------


def test_ensemble_blended_router_route():
    train_df, specs_df = load_data()
    router = GeometricRouter.fit(
        train_df, specs_df,
        use_logistic=True, blend_alpha=0.5,
    )
    assert router.logistic_pass_model is not None
    assert router.blend_alpha == 0.5
    decision = router.route("테스트 프롬프트입니다", budget_tier="balanced")
    assert decision.selected_model_id in list(MODEL_ORDER) + ["abstain"]


def test_ensemble_alpha_one_matches_knn_only():
    train_df, specs_df = load_data()
    router_knn = GeometricRouter.fit(train_df, specs_df, use_logistic=False)
    router_blend = GeometricRouter.fit(
        train_df, specs_df, use_logistic=True, blend_alpha=1.0,
    )
    prompt = "간단한 테스트"
    dec_knn = router_knn.route(prompt, budget_tier="balanced")
    dec_blend = router_blend.route(prompt, budget_tier="balanced")
    assert dec_knn.selected_model_id == dec_blend.selected_model_id


# ---------------------------------------------------------------------------
# Integration Tests (3)
# ---------------------------------------------------------------------------


def test_phase4_router_save_load_round_trip(tmp_path):
    train_df, specs_df = load_data()
    router = GeometricRouter.fit(
        train_df, specs_df,
        use_logistic=True, blend_alpha=0.5,
        use_risk_pca=True, risk_pca_variance=0.90,
    )
    path = tmp_path / "phase4_router.json"
    router.save(path)
    loaded = GeometricRouter.load(path)
    assert loaded.logistic_pass_model is not None
    assert loaded.blend_alpha == 0.5
    assert loaded.risk_model.pca_transform is not None
    prompt = "저장 로드 테스트"
    dec_orig = router.route(prompt, budget_tier="balanced")
    dec_loaded = loaded.route(prompt, budget_tier="balanced")
    assert dec_orig.selected_model_id == dec_loaded.selected_model_id


def test_backward_compatible_load_without_phase4_fields(tmp_path):
    router = make_router()
    path = tmp_path / "legacy_router.json"
    router.save(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("logistic_pass_model", None)
    payload.pop("blend_alpha", None)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    loaded = GeometricRouter.load(path)
    assert loaded.logistic_pass_model is None
    assert loaded.blend_alpha == 1.0
    decision = loaded.route("호환성 테스트", budget_tier="balanced")
    assert decision.selected_model_id in list(MODEL_ORDER) + ["abstain"]


def test_logistic_pass_model_json_serializable():
    prompt_features, labels, _ = _build_features_and_labels()
    model = fit_logistic_pass_model(prompt_features, labels)
    payload = model.to_dict()
    serialized = json.dumps(payload, ensure_ascii=False)
    restored = json.loads(serialized)
    assert set(restored["models"].keys()) == set(MODEL_ORDER)
