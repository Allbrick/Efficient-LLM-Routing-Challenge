from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from router_impls.geometric.router import GeometricRouter


TIER_ORDER = ("fast", "balanced", "premium")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate geometric candidate explanation assets.")
    parser.add_argument("--artifact", default="artifacts/geometric_router.json")
    parser.add_argument("--demo_prompts", default="docs/report_assets/demo_prompts.csv")
    parser.add_argument("--output_dir", default="docs/report_assets")
    args = parser.parse_args()

    router = GeometricRouter.load(args.artifact)
    demo_df = pd.read_csv(args.demo_prompts)
    summary = generate_geometric_explanations(router, demo_df, args.output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def generate_geometric_explanations(
    router: GeometricRouter,
    demo_df: pd.DataFrame,
    output_dir: str | Path = "docs/report_assets",
) -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for row in demo_df.fillna("").itertuples(index=False):
        for tier in TIER_ORDER:
            decision = router.route(
                str(row.prompt),
                budget_tier=tier,
                task_type=str(getattr(row, "task_type", "")),
                difficulty=str(getattr(row, "difficulty", "")),
                risk_level=str(getattr(row, "risk_level", "")),
                evaluation_type=str(getattr(row, "evaluation_type", "")),
            )
            candidates = {candidate["model_id"]: candidate for candidate in decision.candidates}
            frontier = decision.frontier_hint or {}
            rows.append(
                {
                    "demo_case": str(getattr(row, "demo_case", "")),
                    "prompt_id": str(getattr(row, "prompt_id", "")),
                    "tier": tier,
                    "expected_min_model": str(getattr(row, "expected_min_model", "")),
                    "selected_model_id": decision.selected_model_id,
                    "selection_reason": decision.selection_reason,
                    "repetition_ratio": decision.evidence.get("repetition_ratio", 0.0),
                    "compressed_length_norm": decision.evidence.get("compressed_length_norm", 0.0),
                    "cheap_cost": candidates.get("cheap", {}).get("cost", ""),
                    "cheap_normalized_distance": candidates.get("cheap", {}).get("normalized_distance", ""),
                    "cheap_pass_probability": candidates.get("cheap", {}).get("pass_probability", ""),
                    "cheap_sufficiency_probability": candidates.get("cheap", {}).get("sufficiency_probability", ""),
                    "mid_cost": candidates.get("mid", {}).get("cost", ""),
                    "mid_normalized_distance": candidates.get("mid", {}).get("normalized_distance", ""),
                    "mid_pass_probability": candidates.get("mid", {}).get("pass_probability", ""),
                    "mid_sufficiency_probability": candidates.get("mid", {}).get("sufficiency_probability", ""),
                    "premium_cost": candidates.get("premium", {}).get("cost", ""),
                    "premium_normalized_distance": candidates.get("premium", {}).get("normalized_distance", ""),
                    "premium_pass_probability": candidates.get("premium", {}).get("pass_probability", ""),
                    "premium_sufficiency_probability": candidates.get("premium", {}).get("sufficiency_probability", ""),
                    "abstain_probability": candidates.get("abstain", {}).get("pass_probability", ""),
                    "frontier_model": frontier.get("model_id", ""),
                    "frontier_cost": frontier.get("cost", ""),
                    "frontier_quality": frontier.get("quality", ""),
                }
            )
    detail_df = pd.DataFrame(rows)
    summary_df = summarize_explanations(detail_df)
    detail_df.to_csv(output / "geometric_explanations.csv", index=False, encoding="utf-8")
    summary_df.to_csv(output / "geometric_explanations_summary.csv", index=False, encoding="utf-8")
    payload = {
        "output_dir": str(output),
        "files": [
            "geometric_explanations.csv",
            "geometric_explanations_summary.csv",
            "geometric_explanations_summary.json",
        ],
        "summary": summary_df.to_dict(orient="records"),
    }
    (output / "geometric_explanations_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def summarize_explanations(detail_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (demo_case, tier), group in detail_df.groupby(["demo_case", "tier"], sort=False):
        first = group.iloc[0]
        rows.append(
            {
                "demo_case": demo_case,
                "tier": tier,
                "selected_model_id": first["selected_model_id"],
                "selection_reason": first["selection_reason"],
                "cheap_distance": first["cheap_normalized_distance"],
                "mid_distance": first["mid_normalized_distance"],
                "premium_distance": first["premium_normalized_distance"],
                "cheap_pass_probability": first["cheap_pass_probability"],
                "mid_pass_probability": first["mid_pass_probability"],
                "premium_pass_probability": first["premium_pass_probability"],
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    main()
