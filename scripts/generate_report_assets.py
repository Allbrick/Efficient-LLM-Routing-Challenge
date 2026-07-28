from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from router_impls.geometric.budget_allocator import allocate_public_budget
from router_impls.geometric.router import GeometricRouter
from router_impls.geometric.simulator import simulate_public_set
from router_impls.geometric.tuning import score_tier_summary, tune_router_policy
from routing_stack.training.outcome_matrix import merge_outcome_training


TIER_ORDER = ("fast", "balanced", "premium")
DEMO_CASES = (
    {
        "demo_case": "trivial cheap",
        "difficulty": "trivial",
        "risk_level": "low",
        "expected_min_model": "cheap",
        "evaluation_types": {"exact_match"},
    },
    {
        "demo_case": "simple numeric",
        "difficulty": "trivial",
        "risk_level": "low",
        "expected_min_model": "cheap",
        "evaluation_types": {"numeric_check", "numeric_count"},
    },
    {
        "demo_case": "medium code",
        "difficulty": "medium",
        "expected_min_model": "mid",
        "task_contains": "code",
    },
    {
        "demo_case": "hard architecture",
        "difficulty": "hard",
        "risk_level": "high",
        "expected_min_model": "premium",
    },
    {
        "demo_case": "missing context abstain",
        "risk_level": "high",
        "expected_min_model": "abstain",
    },
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate report-ready CSV/JSON assets for geometric routing.")
    parser.add_argument("--train_path", default="data/public/example_train.csv")
    parser.add_argument("--specs_path", default="data/public/example_eval_specs.csv")
    parser.add_argument("--outcome_matrix_path", default="")
    parser.add_argument("--output_dir", default="docs/report_assets")
    parser.add_argument("--semantic_features", action="store_true")
    parser.add_argument("--no_synthetic", action="store_true")
    args = parser.parse_args()

    train_df = pd.read_csv(args.train_path)
    specs_df = pd.read_csv(args.specs_path)
    if args.outcome_matrix_path:
        train_df, specs_df, _summary = merge_outcome_training(train_df, specs_df, args.outcome_matrix_path)
    assets = generate_report_assets(
        train_df=train_df,
        specs_df=specs_df,
        output_dir=args.output_dir,
        use_semantic_features=args.semantic_features,
        include_synthetic=not args.no_synthetic,
    )
    print(json.dumps(assets, ensure_ascii=False, indent=2))


def generate_report_assets(
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame,
    output_dir: str | Path = "docs/report_assets",
    use_semantic_features: bool = False,
    include_synthetic: bool = True,
) -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    baseline_router = GeometricRouter.fit(
        train_df,
        specs_df,
        include_synthetic=include_synthetic,
        use_semantic_features=use_semantic_features,
    )
    baseline_payload = simulate_public_set(baseline_router, train_df, specs_df, tiers=TIER_ORDER)

    tuned_router = GeometricRouter.fit(
        train_df,
        specs_df,
        include_synthetic=include_synthetic,
        use_semantic_features=use_semantic_features,
    )
    tuning = tune_router_policy(tuned_router, train_df, specs_df, tiers=TIER_ORDER)
    tuned_payload = simulate_public_set(tuned_router, train_df, specs_df, tiers=TIER_ORDER)
    allocation_payload = allocate_public_budget(tuned_router, train_df, specs_df, "fast")

    tier_summary = build_tier_summary(tuned_payload["summary"]["tier_summary"])
    selection_distribution = build_selection_distribution(tuned_payload["rows"])
    error_summary = build_error_summary(tuned_payload["rows"])
    before_after = build_before_after_summary(
        baseline_payload["summary"]["tier_summary"],
        tuned_payload["summary"]["tier_summary"],
    )
    demo_prompts = select_demo_prompts(specs_df, tuned_payload["rows"])
    allocation_summary = pd.DataFrame([allocation_payload["summary"]])

    write_csv(output / "tier_summary.csv", tier_summary)
    write_csv(output / "selection_distribution.csv", selection_distribution)
    write_csv(output / "error_summary.csv", error_summary)
    write_csv(output / "before_after.csv", before_after)
    write_csv(output / "demo_prompts.csv", demo_prompts)
    write_csv(output / "fast_allocation_summary.csv", allocation_summary)

    summary = {
        "output_dir": str(output),
        "n_prompts": int(train_df["prompt_id"].nunique()),
        "n_train_rows": int(len(train_df)),
        "semantic_features": bool(use_semantic_features),
        "overall_weighted_score": tuned_router.metadata.get("policy_objective", {}).get("overall_score"),
        "tier_summary": tier_summary.to_dict(orient="records"),
        "before_after": before_after.to_dict(orient="records"),
        "fast_allocation_summary": allocation_payload["summary"],
        "tuning": tuning,
        "files": [
            "tier_summary.csv",
            "selection_distribution.csv",
            "error_summary.csv",
            "before_after.csv",
            "demo_prompts.csv",
            "fast_allocation_summary.csv",
            "report_assets_summary.json",
        ],
    }
    (output / "report_assets_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def build_tier_summary(tier_summary: dict) -> pd.DataFrame:
    rows = []
    for tier in TIER_ORDER:
        summary = tier_summary[tier]
        objective = score_tier_summary(summary, tier)
        rows.append(
            {
                "tier": tier,
                "count": summary["count"],
                "budget_limit": summary["budget_limit"],
                "mean_quality": summary["mean_quality"],
                "mean_cost": summary["mean_cost"],
                "mean_excess_cost": summary["mean_excess_cost"],
                "cost_over_limit": summary["cost_over_limit"],
                "under_route": summary["under_route"],
                "over_route": summary["over_route"],
                "should_abstain": summary["should_abstain"],
                "ok": summary["ok"],
                "weighted_score": objective["weighted_score"],
            }
        )
    return pd.DataFrame(rows)


def build_selection_distribution(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    counts = (
        df.groupby(["budget_tier", "selected_model_id"], sort=False)
        .size()
        .reset_index(name="count")
    )
    total_by_tier = counts.groupby("budget_tier")["count"].transform("sum")
    counts["ratio"] = counts["count"] / total_by_tier
    return counts


def build_error_summary(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    counts = (
        df.groupby(["budget_tier", "error_type"], sort=False)
        .size()
        .reset_index(name="count")
    )
    total_by_tier = counts.groupby("budget_tier")["count"].transform("sum")
    counts["ratio"] = counts["count"] / total_by_tier
    return counts


def build_before_after_summary(baseline_summary: dict, tuned_summary: dict) -> pd.DataFrame:
    rows = []
    metrics = ("mean_quality", "mean_cost", "mean_excess_cost", "cost_over_limit", "under_route", "over_route", "ok")
    for tier in TIER_ORDER:
        before = baseline_summary[tier]
        after = tuned_summary[tier]
        row = {"tier": tier}
        for metric in metrics:
            row[f"before_{metric}"] = before[metric]
            row[f"after_{metric}"] = after[metric]
            row[f"delta_{metric}"] = after[metric] - before[metric]
        row["before_weighted_score"] = score_tier_summary(before, tier)["weighted_score"]
        row["after_weighted_score"] = score_tier_summary(after, tier)["weighted_score"]
        row["delta_weighted_score"] = row["after_weighted_score"] - row["before_weighted_score"]
        rows.append(row)
    return pd.DataFrame(rows)


def select_demo_prompts(specs_df: pd.DataFrame, route_rows: list[dict]) -> pd.DataFrame:
    route_df = pd.DataFrame(route_rows)
    merged = specs_df.merge(
        route_df[["prompt_id", "budget_tier", "selected_model_id", "selection_reason"]],
        on="prompt_id",
        how="left",
    )
    selected_rows = []
    used_prompt_ids = set()
    for case in DEMO_CASES:
        subset = merged[merged["budget_tier"] == "fast"]
        if case.get("difficulty"):
            subset = subset[subset["difficulty"].astype(str) == case["difficulty"]]
        if case.get("risk_level"):
            subset = subset[subset["risk_level"].astype(str) == case["risk_level"]]
        if case.get("expected_min_model"):
            subset = subset[subset["expected_min_model"].astype(str) == case["expected_min_model"]]
        if case.get("evaluation_types"):
            subset = subset[subset["evaluation_type"].astype(str).isin(case["evaluation_types"])]
        if case.get("task_contains"):
            subset = subset[subset["task_type"].astype(str).str.contains(str(case["task_contains"]), case=False, na=False)]
        if subset.empty:
            subset = merged[
                (merged["expected_min_model"].astype(str) == case.get("expected_min_model", ""))
                & (merged["budget_tier"] == "fast")
            ]
        if subset.empty:
            continue
        subset = subset.assign(_prompt_length=subset["prompt"].astype(str).str.len()).sort_values(
            ["_prompt_length", "prompt_id"],
            kind="stable",
        )
        row = subset.iloc[0].to_dict()
        if row["prompt_id"] in used_prompt_ids:
            continue
        used_prompt_ids.add(row["prompt_id"])
        row["demo_case"] = case["demo_case"]
        selected_rows.append(row)

    tier_diff = (
        route_df.groupby("prompt_id")["selected_model_id"]
        .nunique()
        .reset_index(name="selection_variants")
    )
    tier_diff = tier_diff[tier_diff["selection_variants"] > 1]
    if not tier_diff.empty:
        prompt_id = str(tier_diff.iloc[0]["prompt_id"])
        if prompt_id not in used_prompt_ids:
            row = merged[(merged["prompt_id"].astype(str) == prompt_id) & (merged["budget_tier"] == "fast")].iloc[0].to_dict()
            row["demo_case"] = "tier-dependent selection"
            selected_rows.append(row)

    columns = [
        "demo_case",
        "prompt_id",
        "prompt",
        "task_type",
        "difficulty",
        "risk_level",
        "expected_min_model",
        "evaluation_type",
        "selected_model_id",
        "selection_reason",
    ]
    return pd.DataFrame(selected_rows)[columns]


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")


if __name__ == "__main__":
    main()
