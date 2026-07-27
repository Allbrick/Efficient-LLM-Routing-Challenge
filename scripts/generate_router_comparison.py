from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from router_impls.geometric.evaluator import build_training_labels
from router_impls.geometric.features import MODEL_RANK
from router_impls.geometric.router import BUDGET_LIMITS, GeometricRouter
from router_impls.geometric.simulator import classify_route


TIER_ORDER = ("fast", "balanced", "premium")
FIXED_ROUTERS = {
    "always_cheap": "cheap",
    "always_mid": "mid",
    "always_premium": "premium",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate baseline-vs-geometric router comparison assets.")
    parser.add_argument("--train_path", default="data/public/example_train.csv")
    parser.add_argument("--specs_path", default="data/public/example_eval_specs.csv")
    parser.add_argument("--artifact", default="artifacts/geometric_router.json")
    parser.add_argument("--external_artifact", default="artifacts/geometric_router_external.json")
    parser.add_argument("--output_dir", default="docs/report_assets")
    args = parser.parse_args()

    train_df = pd.read_csv(args.train_path)
    specs_df = pd.read_csv(args.specs_path)
    summary = generate_router_comparison(
        train_df=train_df,
        specs_df=specs_df,
        artifact=args.artifact,
        external_artifact=args.external_artifact,
        output_dir=args.output_dir,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def generate_router_comparison(
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame,
    artifact: str | Path = "artifacts/geometric_router.json",
    external_artifact: str | Path = "artifacts/geometric_router_external.json",
    output_dir: str | Path = "docs/report_assets",
) -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    labels = build_training_labels(train_df, specs_df)
    expected_by_prompt = labels.drop_duplicates("prompt_id").set_index("prompt_id")["expected_min_model"].to_dict()
    spec_map = {row.prompt_id: row._asdict() for row in specs_df.fillna("").itertuples(index=False)}

    rows = []
    for router_name, model_id in FIXED_ROUTERS.items():
        rows.extend(evaluate_fixed_router(router_name, model_id, train_df, expected_by_prompt))

    if Path(artifact).exists():
        rows.extend(evaluate_geometric_router("geometric_tuned", GeometricRouter.load(artifact), train_df, spec_map, expected_by_prompt))
    if Path(external_artifact).exists():
        rows.extend(
            evaluate_geometric_router(
                "geometric_external_weak",
                GeometricRouter.load(external_artifact),
                train_df,
                spec_map,
                expected_by_prompt,
            )
        )

    detail_df = pd.DataFrame(rows)
    summary_df = summarize_comparison(detail_df)
    detail_path = output / "router_comparison_detail.csv"
    summary_path = output / "router_comparison.csv"
    detail_df.to_csv(detail_path, index=False, encoding="utf-8")
    summary_df.to_csv(summary_path, index=False, encoding="utf-8")

    payload = {
        "output_dir": str(output),
        "routers": sorted(detail_df["router"].unique().tolist()) if not detail_df.empty else [],
        "tiers": list(TIER_ORDER),
        "files": ["router_comparison.csv", "router_comparison_detail.csv", "router_comparison_summary.json"],
        "summary": summary_df.to_dict(orient="records"),
    }
    (output / "router_comparison_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def evaluate_fixed_router(
    router_name: str,
    model_id: str,
    train_df: pd.DataFrame,
    expected_by_prompt: dict[str, str],
) -> list[dict]:
    rows = []
    for prompt_id, group in train_df.groupby("prompt_id", sort=False):
        selected_row = group[group["model_id"] == model_id].iloc[0]
        expected = expected_by_prompt[prompt_id]
        for tier in TIER_ORDER:
            rows.append(
                {
                    "router": router_name,
                    "prompt_id": prompt_id,
                    "budget_tier": tier,
                    "expected_min_model": expected,
                    "selected_model_id": model_id,
                    "actual_quality": float(selected_row["quality_score"]),
                    "cost": float(selected_row["cost"]),
                    "error_type": classify_route(expected, model_id),
                    "selection_reason": "fixed_policy",
                    "latency_ms": 0.0,
                }
            )
    return rows


def evaluate_geometric_router(
    router_name: str,
    router: GeometricRouter,
    train_df: pd.DataFrame,
    spec_map: dict,
    expected_by_prompt: dict[str, str],
) -> list[dict]:
    rows = []
    for prompt_id, group in train_df.groupby("prompt_id", sort=False):
        first = group.iloc[0]
        spec = spec_map.get(prompt_id, {})
        expected = expected_by_prompt[prompt_id]
        for tier in TIER_ORDER:
            started = time.perf_counter()
            decision = router.route(
                str(first["prompt"]),
                budget_tier=tier,
                task_type=str(spec.get("task_type", "")),
                difficulty=str(spec.get("difficulty", "")),
                risk_level=str(spec.get("risk_level", "")),
                evaluation_type=str(spec.get("evaluation_type", "")),
            )
            latency_ms = (time.perf_counter() - started) * 1000.0
            if decision.selected_model_id == "abstain":
                actual_quality = 1.0 if expected == "abstain" else 0.0
                cost = 0.0
            else:
                selected_row = group[group["model_id"] == decision.selected_model_id].iloc[0]
                actual_quality = float(selected_row["quality_score"])
                cost = float(selected_row["cost"])
            rows.append(
                {
                    "router": router_name,
                    "prompt_id": prompt_id,
                    "budget_tier": tier,
                    "expected_min_model": expected,
                    "selected_model_id": decision.selected_model_id,
                    "actual_quality": actual_quality,
                    "cost": cost,
                    "error_type": classify_route(expected, decision.selected_model_id),
                    "selection_reason": decision.selection_reason,
                    "latency_ms": latency_ms,
                }
            )
    return rows


def summarize_comparison(detail_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (router_name, tier), group in detail_df.groupby(["router", "budget_tier"], sort=False):
        budget = BUDGET_LIMITS[tier]
        excess = (group["cost"] - budget).clip(lower=0.0)
        rows.append(
            {
                "router": router_name,
                "tier": tier,
                "count": int(len(group)),
                "mean_quality": float(group["actual_quality"].mean()),
                "mean_cost": float(group["cost"].mean()),
                "mean_excess_cost": float(excess.mean()),
                "cost_over_limit": int((group["cost"] > budget).sum()),
                "under_route": int((group["error_type"] == "under_route").sum()),
                "over_route": int((group["error_type"] == "over_route").sum()),
                "should_abstain": int((group["error_type"] == "should_abstain").sum()),
                "ok": int((group["error_type"] == "ok").sum()),
                "latency_ms_mean": float(group["latency_ms"].mean()),
                "selection_counts": json.dumps(group["selected_model_id"].value_counts().to_dict(), ensure_ascii=False),
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    main()
