from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from geometric_router.evaluator import build_training_labels
from geometric_router.features import MODEL_RANK
from geometric_router.router import BUDGET_LIMITS, GeometricRouter


@dataclass(frozen=True)
class AllocationChoice:
    prompt_id: str
    selected_model_id: str
    predicted_score: float
    actual_quality: float
    cost: float
    expected_min_model: str
    error_type: str


def allocate_public_budget(
    router: GeometricRouter,
    train_df: pd.DataFrame,
    specs_df: pd.DataFrame | None,
    tier: str,
    fallback_threshold: float = 0.85,
    cost_scale: int = 100,
) -> dict:
    """Allocate one tier budget across the whole public prompt set.

    This is a batch simulator. It does not claim private-test access to future
    prompts; it is used to tune and inspect budget-aware behavior.
    """
    tier = tier.lower()
    if tier not in BUDGET_LIMITS:
        raise ValueError(f"unknown tier: {tier}")

    labels = build_training_labels(train_df, specs_df, fallback_threshold=fallback_threshold)
    expected_by_prompt = labels.drop_duplicates("prompt_id").set_index("prompt_id")["expected_min_model"].to_dict()
    spec_map = {}
    if specs_df is not None and not specs_df.empty:
        spec_map = {row.prompt_id: row._asdict() for row in specs_df.itertuples(index=False)}

    prompt_options = []
    prompt_ids = []
    for prompt_id, group in train_df.groupby("prompt_id", sort=False):
        first = group.iloc[0]
        spec = spec_map.get(prompt_id, {})
        decision = router.route(
            first["prompt"],
            budget_tier=tier,
            task_type=str(spec.get("task_type", first.get("task_type", ""))),
            difficulty=str(spec.get("difficulty", "")),
            risk_level=str(spec.get("risk_level", "")),
            evaluation_type=str(spec.get("evaluation_type", "")),
        )
        rows_by_model = group.set_index("model_id")
        options = []
        for candidate in decision.candidates:
            model_id = candidate["model_id"]
            actual_row = rows_by_model.loc[model_id]
            options.append(
                {
                    "model_id": model_id,
                    "cost_units": int(round(float(candidate["cost"]) * cost_scale)),
                    "cost": float(candidate["cost"]),
                    "predicted_score": _candidate_score(candidate),
                    "actual_quality": float(actual_row["quality_score"]),
                }
            )
        prompt_ids.append(prompt_id)
        prompt_options.append(options)

    budget_units = int(round(BUDGET_LIMITS[tier] * len(prompt_ids) * cost_scale))
    choices = _dynamic_program(prompt_options, budget_units)

    allocated = []
    for prompt_id, option in zip(prompt_ids, choices):
        expected = expected_by_prompt[prompt_id]
        selected = option["model_id"]
        allocated.append(
            AllocationChoice(
                prompt_id=prompt_id,
                selected_model_id=selected,
                predicted_score=float(option["predicted_score"]),
                actual_quality=float(option["actual_quality"]),
                cost=float(option["cost"]),
                expected_min_model=expected,
                error_type=_classify(expected, selected),
            )
        )

    result_df = pd.DataFrame([row.__dict__ for row in allocated])
    excess = (result_df["cost"] - BUDGET_LIMITS[tier]).clip(lower=0.0)
    total_budget = BUDGET_LIMITS[tier] * len(result_df)
    total_cost = float(result_df["cost"].sum())
    summary = {
        "tier": tier,
        "count": int(len(result_df)),
        "budget_limit": float(BUDGET_LIMITS[tier]),
        "total_budget": round(float(total_budget), 10),
        "total_cost": round(total_cost, 10),
        "mean_quality": float(result_df["actual_quality"].mean()),
        "mean_cost": float(result_df["cost"].mean()),
        "mean_excess_cost": float(excess.mean()),
        "cost_over_limit": int((result_df["cost"] > BUDGET_LIMITS[tier]).sum()),
        "under_route": int((result_df["error_type"] == "under_route").sum()),
        "over_route": int((result_df["error_type"] == "over_route").sum()),
        "ok": int((result_df["error_type"] == "ok").sum()),
        "selection_counts": result_df["selected_model_id"].value_counts().to_dict(),
    }
    return {"summary": summary, "rows": result_df.to_dict(orient="records")}


def _candidate_score(candidate: dict) -> float:
    pass_probability = float(candidate.get("pass_probability", 0.0))
    sufficiency_probability = float(candidate.get("sufficiency_probability", pass_probability))
    feasible_bonus = 0.08 if candidate.get("feasible") else 0.0
    distance_penalty = 0.04 * float(candidate.get("normalized_distance", 1.0))
    return 0.70 * sufficiency_probability + 0.30 * pass_probability + feasible_bonus - distance_penalty


def _dynamic_program(prompt_options: list[list[dict]], budget_units: int) -> list[dict]:
    states: dict[int, tuple[float, list[int]]] = {0: (0.0, [])}
    for options in prompt_options:
        next_states: dict[int, tuple[float, list[int]]] = {}
        for used_cost, (score, path) in states.items():
            for idx, option in enumerate(options):
                new_cost = used_cost + int(option["cost_units"])
                if new_cost > budget_units:
                    continue
                new_score = score + float(option["predicted_score"])
                current = next_states.get(new_cost)
                if current is None or new_score > current[0]:
                    next_states[new_cost] = (new_score, path + [idx])
        states = next_states
        if not states:
            raise RuntimeError("budget is too small to allocate at least one model per prompt")

    best_cost, (_best_score, best_path) = max(states.items(), key=lambda item: (item[1][0], item[0]))
    _ = best_cost
    return [options[idx] for options, idx in zip(prompt_options, best_path)]


def _classify(expected: str, selected: str) -> str:
    if expected == selected:
        return "ok"
    if MODEL_RANK[selected] < MODEL_RANK[expected]:
        return "under_route"
    return "over_route"
