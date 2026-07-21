from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from router_impls.geometric.evaluator import build_training_labels
from router_impls.geometric.features import MODEL_RANK
from router_impls.geometric.router import BUDGET_LIMITS, GeometricRouter


@dataclass(frozen=True)
class SimulationRow:
    prompt_id: str
    budget_tier: str
    expected_min_model: str
    selected_model_id: str
    actual_quality: float
    cost: float
    error_type: str
    selection_reason: str


def classify_route(expected: str, selected: str) -> str:
    if expected == selected:
        return "ok"
    if expected == "abstain":
        return "should_abstain"
    if selected == "abstain":
        return "under_route"
    if MODEL_RANK[selected] < MODEL_RANK[expected]:
        return "under_route"
    return "over_route"


def simulate_public_set(
    router: GeometricRouter,
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame | None = None,
    tiers: tuple[str, ...] = ("fast", "balanced", "premium"),
    fallback_threshold: float = 0.85,
) -> dict:
    labels = build_training_labels(train_df, specs_df, fallback_threshold=fallback_threshold)
    expected_by_prompt = labels.drop_duplicates("prompt_id").set_index("prompt_id")["expected_min_model"].to_dict()
    spec_map = {}
    if specs_df is not None and not specs_df.empty:
        spec_map = {row.prompt_id: row._asdict() for row in specs_df.itertuples(index=False)}

    rows: list[SimulationRow] = []
    for prompt_id, group in train_df.groupby("prompt_id", sort=False):
        first = group.iloc[0]
        spec = spec_map.get(prompt_id, {})
        expected = expected_by_prompt[prompt_id]
        for tier in tiers:
            decision = router.route(
                first["prompt"],
                budget_tier=tier,
                task_type=str(spec.get("task_type", first.get("task_type", ""))),
                difficulty=str(spec.get("difficulty", "")),
                risk_level=str(spec.get("risk_level", "")),
                evaluation_type=str(spec.get("evaluation_type", "")),
            )
            if decision.selected_model_id == "abstain":
                actual_quality = 1.0 if expected == "abstain" else 0.0
                cost = 0.0
            else:
                selected_row = group[group["model_id"] == decision.selected_model_id].iloc[0]
                actual_quality = float(selected_row["quality_score"])
                cost = float(selected_row["cost"])
            rows.append(
                SimulationRow(
                    prompt_id=prompt_id,
                    budget_tier=tier,
                    expected_min_model=expected,
                    selected_model_id=decision.selected_model_id,
                    actual_quality=actual_quality,
                    cost=cost,
                    error_type=classify_route(expected, decision.selected_model_id),
                    selection_reason=decision.selection_reason,
                )
            )

    result_df = pd.DataFrame([row.__dict__ for row in rows])
    tier_summary = {}
    for tier, group in result_df.groupby("budget_tier", sort=False):
        budget_limit = BUDGET_LIMITS[tier]
        excess = (group["cost"] - budget_limit).clip(lower=0.0)
        tier_summary[tier] = {
            "count": int(len(group)),
            "budget_limit": float(budget_limit),
            "mean_quality": float(group["actual_quality"].mean()),
            "mean_cost": float(group["cost"].mean()),
            "mean_excess_cost": float(excess.mean()),
            "cost_over_limit": int((group["cost"] > budget_limit).sum()),
            "under_route": int((group["error_type"] == "under_route").sum()),
            "over_route": int((group["error_type"] == "over_route").sum()),
            "should_abstain": int((group["error_type"] == "should_abstain").sum()),
            "ok": int((group["error_type"] == "ok").sum()),
            "selection_counts": group["selected_model_id"].value_counts().to_dict(),
        }

    return {
        "summary": {
            "n_prompts": int(train_df["prompt_id"].nunique()),
            "n_rows": int(len(result_df)),
            "tier_summary": tier_summary,
        },
        "rows": result_df.to_dict(orient="records"),
    }


