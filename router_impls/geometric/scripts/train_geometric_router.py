from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from router_impls.geometric.classification_metrics import (
    compute_classification_report,
    compute_roc_auc,
    compute_routing_confusion_matrix,
)
from router_impls.geometric.cross_validation import cross_validate_router
from router_impls.geometric.evaluator import build_training_labels
from router_impls.geometric.router import GeometricRouter
from router_impls.geometric.simulator import simulate_public_set
from router_impls.geometric.tuning import tune_router_policy
from routing_stack.training.data_quality import validate_training_data
from routing_stack.training.external_training import load_training_with_external
from routing_stack.training.feedback_training import merge_feedback_training
from routing_stack.training.outcome_matrix import merge_outcome_training


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the geometric LLM router MVP.")
    parser.add_argument("--train_path", default="data/public/example_train.csv")
    parser.add_argument("--specs_path", default="data/public/example_eval_specs.csv")
    parser.add_argument("--external_specs_path", default="")
    parser.add_argument("--include_external", action="store_true")
    parser.add_argument("--include_feedback", action="store_true")
    parser.add_argument("--feedback_path", default="data/router_feedback/online_feedback.csv")
    parser.add_argument("--outcome_matrix_path", default="")
    parser.add_argument("--output", default="artifacts/geometric_router.json")
    parser.add_argument("--labels_output", default="artifacts/geometric_labels.csv")
    parser.add_argument("--policy_report", default="artifacts/geometric_policy_report.json")
    parser.add_argument("--fallback_threshold", type=float, default=0.85)
    parser.add_argument("--radius_quantile", type=float, default=0.90)
    parser.add_argument("--no_synthetic", action="store_true")
    parser.add_argument("--no_tune", action="store_true")
    parser.add_argument("--semantic_features", action="store_true")
    parser.add_argument("--quality-check", action="store_true", help="Run data quality validation before training")
    parser.add_argument("--cross-validate", action="store_true", help="Run K-fold cross-validation after training")
    parser.add_argument("--cv-folds", type=int, default=5, help="Number of folds for cross-validation (default: 5)")
    args = parser.parse_args()

    train_df, specs_df, data_summary = load_training_with_external(
        args.train_path,
        args.specs_path,
        args.external_specs_path if args.include_external else None,
    )
    if args.include_feedback:
        train_df, specs_df, feedback_summary = merge_feedback_training(train_df, specs_df, args.feedback_path)
        data_summary.update(feedback_summary)
    if args.outcome_matrix_path:
        train_df, specs_df, outcome_summary = merge_outcome_training(train_df, specs_df, args.outcome_matrix_path)
        data_summary.update(outcome_summary)

    # --- Data quality check ---
    dq_report_dict = None
    if getattr(args, "quality_check", False):
        print("Running data quality validation...")
        dq_report = validate_training_data(train_df, specs_df, fallback_threshold=args.fallback_threshold)
        dq_report_dict = dq_report.to_dict()
        dq_path = Path("artifacts/data_quality_report.json")
        dq_path.parent.mkdir(parents=True, exist_ok=True)
        dq_path.write_text(json.dumps(dq_report_dict, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Warnings: {len(dq_report.warnings)}, Errors: {len(dq_report.errors)}")
        for w in dq_report.warnings:
            print(f"  [WARN] {w}")
        for e in dq_report.errors:
            print(f"  [ERROR] {e}")
        print(f"  Data quality report saved to {dq_path}")

    router = GeometricRouter.fit(
        train_df,
        specs_df,
        fallback_threshold=args.fallback_threshold,
        radius_quantile=args.radius_quantile,
        include_synthetic=not args.no_synthetic,
        use_semantic_features=args.semantic_features,
    )
    tuning = None
    if not args.no_tune:
        tuning = tune_router_policy(router, train_df, specs_df)
    router.save(args.output)

    labels = build_training_labels(train_df, specs_df, fallback_threshold=args.fallback_threshold)
    labels_path = Path(args.labels_output)
    labels_path.parent.mkdir(parents=True, exist_ok=True)
    labels.to_csv(labels_path, index=False)

    # --- Cross-validation and classification metrics ---
    cv_report_dict = None
    if getattr(args, "cross_validate", False):
        print(f"Running {args.cv_folds}-fold cross-validation...")
        cv_result = cross_validate_router(
            train_df,
            specs_df,
            n_folds=args.cv_folds,
            fallback_threshold=args.fallback_threshold,
            radius_quantile=args.radius_quantile,
            include_synthetic=not args.no_synthetic,
        )
        print(f"  CV completed in {cv_result.total_time_seconds:.1f}s")
        agg = cv_result.aggregated.get("overall_weighted_score", {})
        print(f"  Overall weighted score: {agg.get('mean', 0):.4f} +/- {agg.get('std', 0):.4f}")

        # Classification metrics on full simulation
        sim_payload = simulate_public_set(router, train_df, specs_df)
        confusion = {}
        clf_report = {}
        for tier in ("fast", "balanced", "premium"):
            confusion[tier] = compute_routing_confusion_matrix(sim_payload["rows"], tier=tier)
            clf_report[tier] = compute_classification_report(sim_payload["rows"], tier=tier)

        roc_auc = compute_roc_auc(router, train_df, specs_df, fallback_threshold=args.fallback_threshold)

        cv_report_dict = {
            "cross_validation": cv_result.to_dict(),
            "classification_metrics": {
                "confusion_matrix": confusion,
                "classification_report": clf_report,
                "roc_auc": roc_auc,
            },
        }
        cv_path = Path("artifacts/cross_validation_report.json")
        cv_path.parent.mkdir(parents=True, exist_ok=True)
        cv_path.write_text(json.dumps(cv_report_dict, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Cross-validation report saved to {cv_path}")

    summary = {
        "artifact": args.output,
        "labels": args.labels_output,
        "policy_report": args.policy_report,
        "metadata": router.metadata,
        "data": data_summary,
        "envelopes": {
            model: {
                "sample_count": envelope.sample_count,
                "radius": envelope.radius,
            }
            for model, envelope in router.envelopes.items()
        },
        "frontier": router.frontier,
        "policy": {
            "radius_multipliers": router.radius_multipliers,
            "fallback_cost_weight": router.fallback_cost_weight,
            "pass_thresholds": router.pass_thresholds,
            "abstain_thresholds": router.abstain_thresholds,
            "tuning": tuning,
        },
    }
    if dq_report_dict is not None:
        summary["data_quality"] = dq_report_dict
    if cv_report_dict is not None:
        summary["cross_validation"] = cv_report_dict

    report_path = Path(args.policy_report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


