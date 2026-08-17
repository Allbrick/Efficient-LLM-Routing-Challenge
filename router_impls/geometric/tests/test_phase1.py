from __future__ import annotations

import json

from router_impls.geometric.classification_metrics import (
    compute_classification_report,
    compute_roc_auc,
    compute_routing_confusion_matrix,
)
from router_impls.geometric.cross_validation import CrossValidationResult, cross_validate_router
from router_impls.geometric.simulator import simulate_public_set
from router_impls.geometric.tests.test_geometric_router import load_data, make_router
from routing_stack.training.data_quality import validate_training_data


# ── Cross-validation tests ──────────────────────────────────────────────


def test_cross_validation_runs_and_returns_fold_results():
    train_df, specs_df = load_data()
    result = cross_validate_router(train_df, specs_df, n_folds=3)

    assert isinstance(result, CrossValidationResult)
    assert result.n_folds == 3
    assert len(result.fold_results) == 3
    for fr in result.fold_results:
        assert fr.n_train_prompts > 0
        assert fr.n_val_prompts > 0
        assert fr.fit_time_seconds >= 0
        assert fr.simulate_time_seconds >= 0


def test_cross_validation_aggregated_has_mean_and_std():
    train_df, specs_df = load_data()
    result = cross_validate_router(train_df, specs_df, n_folds=3)

    agg = result.aggregated
    for tier in ("fast", "balanced", "premium"):
        assert tier in agg
        for metric in ("mean_quality", "mean_cost", "weighted_score"):
            assert "mean" in agg[tier][metric]
            assert "std" in agg[tier][metric]

    assert "overall_weighted_score" in agg
    assert "mean" in agg["overall_weighted_score"]
    assert "std" in agg["overall_weighted_score"]


def test_cross_validation_prompts_do_not_leak():
    train_df, specs_df = load_data()
    result = cross_validate_router(train_df, specs_df, n_folds=3)

    total_val_prompts = sum(fr.n_val_prompts for fr in result.fold_results)
    unique_prompts = train_df["prompt_id"].nunique()

    # Total validation prompts across folds should equal unique prompts
    assert total_val_prompts == unique_prompts


def test_cross_validation_to_dict_serializable():
    train_df, specs_df = load_data()
    result = cross_validate_router(train_df, specs_df, n_folds=3)

    d = result.to_dict()
    serialized = json.dumps(d, ensure_ascii=False)
    assert isinstance(serialized, str)
    parsed = json.loads(serialized)
    assert parsed["n_folds"] == 3
    assert len(parsed["fold_results"]) == 3


# ── Classification metrics tests ────────────────────────────────────────


def test_confusion_matrix_has_correct_shape():
    train_df, specs_df = load_data()
    router = make_router()
    payload = simulate_public_set(router, train_df, specs_df)

    cm = compute_routing_confusion_matrix(payload["rows"], tier="fast")

    assert len(cm["labels"]) == 4
    assert len(cm["matrix"]) == 4
    assert all(len(row) == 4 for row in cm["matrix"])
    assert cm["tier"] == "fast"
    assert cm["total_samples"] > 0


def test_classification_report_has_per_class_metrics():
    train_df, specs_df = load_data()
    router = make_router()
    payload = simulate_public_set(router, train_df, specs_df)

    report = compute_classification_report(payload["rows"], tier="balanced")

    assert "per_class" in report
    assert "accuracy" in report
    assert "macro_avg" in report
    assert "weighted_avg" in report
    # Check at least one class has precision/recall/f1
    for label, metrics in report["per_class"].items():
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1-score" in metrics
        break


def test_roc_auc_returns_per_model_scores():
    train_df, specs_df = load_data()
    router = make_router()

    roc = compute_roc_auc(router, train_df, specs_df)

    assert "cheap" in roc
    assert "mid" in roc
    assert "premium" in roc
    # At least one model should have a valid AUC score
    valid_scores = [v for v in roc.values() if v is not None]
    assert len(valid_scores) > 0
    for score in valid_scores:
        assert 0.0 <= score <= 1.0


# ── Data quality tests ──────────────────────────────────────────────────


def test_data_quality_report_structure():
    train_df, specs_df = load_data()

    report = validate_training_data(train_df, specs_df)

    assert hasattr(report, "missing_values")
    assert hasattr(report, "quality_range")
    assert hasattr(report, "cost_validation")
    assert hasattr(report, "model_ordering_anomalies")
    assert hasattr(report, "outliers_iqr")
    assert hasattr(report, "outliers_esd")
    assert hasattr(report, "class_distribution")
    assert hasattr(report, "completeness")
    assert hasattr(report, "warnings")
    assert hasattr(report, "errors")


def test_data_quality_no_errors_on_valid_data():
    train_df, specs_df = load_data()

    report = validate_training_data(train_df, specs_df)

    # The public example data should have no errors (all quality in [0,1], no negatives, etc.)
    assert len(report.errors) == 0


def test_data_quality_detects_out_of_range():
    train_df, specs_df = load_data()

    # Inject an out-of-range quality score
    bad_df = train_df.copy()
    bad_df.loc[bad_df.index[0], "quality_score"] = 1.5

    report = validate_training_data(bad_df, specs_df)

    assert report.quality_range["out_of_range_count"] > 0
    assert any("outside [0, 1]" in e for e in report.errors)


def test_data_quality_to_dict_serializable():
    train_df, specs_df = load_data()

    report = validate_training_data(train_df, specs_df)
    d = report.to_dict()
    serialized = json.dumps(d, ensure_ascii=False)
    assert isinstance(serialized, str)
    parsed = json.loads(serialized)
    assert "missing_values" in parsed
    assert "quality_range" in parsed
