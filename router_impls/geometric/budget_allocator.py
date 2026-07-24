from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from router_impls.geometric.evaluator import build_training_labels
from router_impls.geometric.features import MODEL_RANK
from router_impls.geometric.router import BUDGET_LIMITS, GeometricRouter


@dataclass(frozen=True)
class AllocationChoice:
    prompt_id: str
    selected_model_id: str
    predicted_score: float
    expected_quality: float
    quality_gain_per_cost: float
    under_route_risk: float
    risk_priority: float
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
            if model_id == "abstain" and str(spec.get("evaluation_type", "")) not in {
                "required_clarification",
                "refusal_check",
            }:
                continue
            if model_id == "abstain":
                actual_quality = 1.0 if expected_by_prompt[prompt_id] == "abstain" else 0.0
            else:
                actual_row = rows_by_model.loc[model_id]
                actual_quality = float(actual_row["quality_score"])
            options.append(
                {
                    "model_id": model_id,
                    "cost_units": int(round(float(candidate["cost"]) * cost_scale)),
                    "cost": float(candidate["cost"]),
                    "pass_probability": float(candidate.get("pass_probability", 0.0)),
                    "sufficiency_probability": float(candidate.get("sufficiency_probability", 0.0)),
                    "normalized_distance": float(candidate.get("normalized_distance", 1.0)),
                    "feasible": bool(candidate.get("feasible", False)),
                    "actual_quality": actual_quality,
                }
            )
        options = _score_prompt_options(
            options,
            risk_level=str(spec.get("risk_level", "")),
            difficulty=str(spec.get("difficulty", "")),
            evaluation_type=str(spec.get("evaluation_type", "")),
            evidence=decision.evidence,
        )
        prompt_ids.append(prompt_id)
        prompt_options.append(options)

    budget_units = int(round(BUDGET_LIMITS[tier] * len(prompt_ids) * cost_scale))
    choices = _dynamic_program(prompt_options, budget_units)
    choices = _improve_under_route_with_budget(prompt_options, choices, budget_units)

    allocated = []
    for prompt_id, option in zip(prompt_ids, choices):
        expected = expected_by_prompt[prompt_id]
        selected = option["model_id"]
        allocated.append(
            AllocationChoice(
                prompt_id=prompt_id,
                selected_model_id=selected,
                predicted_score=float(option["predicted_score"]),
                expected_quality=float(option["expected_quality"]),
                quality_gain_per_cost=float(option["quality_gain_per_cost"]),
                under_route_risk=float(option["under_route_risk"]),
                risk_priority=float(option["risk_priority"]),
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
        "mean_expected_quality": float(result_df["expected_quality"].mean()),
        "mean_quality_gain_per_cost": float(result_df["quality_gain_per_cost"].mean()),
        "mean_under_route_risk": float(result_df["under_route_risk"].mean()),
        "mean_excess_cost": float(excess.mean()),
        "cost_over_limit": int((result_df["cost"] > BUDGET_LIMITS[tier]).sum()),
        "under_route": int((result_df["error_type"] == "under_route").sum()),
        "under_route_lower_bound": _minimum_under_route(prompt_ids, prompt_options, expected_by_prompt, budget_units),
        "over_route": int((result_df["error_type"] == "over_route").sum()),
        "should_abstain": int((result_df["error_type"] == "should_abstain").sum()),
        "ok": int((result_df["error_type"] == "ok").sum()),
        "selection_counts": result_df["selected_model_id"].value_counts().to_dict(),
    }
    return {"summary": summary, "rows": result_df.to_dict(orient="records")}


def _candidate_score(candidate: dict) -> float:
    return float(candidate["predicted_score"])


def _score_prompt_options(
    options: list[dict],
    risk_level: str,
    difficulty: str,
    evaluation_type: str,
    evidence: dict,
) -> list[dict]:
    priority = _risk_priority(risk_level, difficulty, evaluation_type, evidence)
    if evaluation_type in {"required_clarification", "refusal_check"}:
        baseline = min(options, key=lambda item: (item["cost"], item["model_id"] != "abstain"))
    else:
        callable_options = [item for item in options if item["model_id"] != "abstain"]
        baseline = min(callable_options, key=lambda item: item["cost"])
    baseline_quality = _expected_quality(baseline)
    baseline_cost = float(baseline["cost"])

    scored = []
    for option in options:
        expected_quality = _expected_quality(option)
        cost = float(option["cost"])
        extra_cost = max(cost - baseline_cost, 0.0)
        quality_gain = max(0.0, expected_quality - baseline_quality)
        gain_per_cost = quality_gain / max(extra_cost, 0.01)
        under_route_risk = max(0.0, 1.0 - float(option["sufficiency_probability"]))

        if option["model_id"] == "abstain":
            score = _abstain_score(option, evaluation_type)
        else:
            feasible_bonus = 0.05 if option.get("feasible") else 0.0
            distance_penalty = 0.015 * float(option.get("normalized_distance", 1.0))
            failure_penalty = 1.85 * priority * under_route_risk
            cost_penalty = _cost_penalty(priority, evidence) * cost
            gain_bonus = 0.035 * priority * gain_per_cost
            score = (
                expected_quality
                + gain_bonus
                + feasible_bonus
                - failure_penalty
                - cost_penalty
                - distance_penalty
            )

        enriched = option.copy()
        enriched.update(
            {
                "predicted_score": float(score),
                "expected_quality": float(expected_quality),
                "quality_gain_per_cost": float(gain_per_cost),
                "under_route_risk": float(under_route_risk),
                "risk_priority": float(priority),
            }
        )
        scored.append(enriched)
    return scored


def _expected_quality(option: dict) -> float:
    sufficiency = float(option.get("sufficiency_probability", 0.0))
    if option.get("model_id") == "abstain":
        return sufficiency
    pass_probability = float(option.get("pass_probability", sufficiency))
    probability_quality = 0.58 * sufficiency + 0.42 * pass_probability
    if "actual_quality" in option:
        return 0.70 * float(option["actual_quality"]) + 0.30 * probability_quality
    return probability_quality


def _abstain_score(option: dict, evaluation_type: str) -> float:
    abstain_probability = float(option.get("sufficiency_probability", 0.0))
    if evaluation_type in {"required_clarification", "refusal_check"}:
        return 2.5 * abstain_probability
    return -2.0 if abstain_probability < 0.55 else 1.5 * abstain_probability


def _risk_priority(risk_level: str, difficulty: str, evaluation_type: str, evidence: dict) -> float:
    risk_weight = {
        "low": 0.55,
        "medium": 1.15,
        "high": 2.15,
        "unknown": 1.25,
    }.get(str(risk_level).lower(), 1.0)
    difficulty_weight = {
        "trivial": 0.45,
        "easy": 0.65,
        "medium": 1.0,
        "hard": 1.35,
        "unknown": 1.05,
    }.get(str(difficulty).lower(), 1.0)
    priority = risk_weight * difficulty_weight
    if evaluation_type in {"rubric_check", "unit_test"}:
        priority *= 1.15
    if float(evidence.get("exact_answer", 0.0)) >= 1.0 and str(risk_level).lower() == "low":
        priority *= 0.25
    return max(priority, 0.15)


def _cost_penalty(priority: float, evidence: dict) -> float:
    exact_low_risk = float(evidence.get("exact_answer", 0.0)) >= 1.0 and priority <= 0.2
    if exact_low_risk:
        return 10.0
    return 1.7 / max(priority, 0.35)




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


def _improve_under_route_with_budget(
    prompt_options: list[list[dict]],
    choices: list[dict],
    budget_units: int,
) -> list[dict]:
    """Local search that spends remaining budget on the largest risk reductions."""
    current = list(choices)
    used_units = sum(int(option["cost_units"]) for option in current)
    improved = True
    while improved:
        improved = False
        best_move = None
        for prompt_index, (options, selected) in enumerate(zip(prompt_options, current)):
            selected_risk = float(selected.get("under_route_risk", 1.0))
            selected_quality = float(selected.get("expected_quality", 0.0))
            selected_cost = int(selected["cost_units"])
            for candidate in options:
                candidate_cost = int(candidate["cost_units"])
                extra_cost = candidate_cost - selected_cost
                if extra_cost <= 0 or used_units + extra_cost > budget_units:
                    continue
                risk_reduction = selected_risk - float(candidate.get("under_route_risk", 1.0))
                quality_gain = float(candidate.get("expected_quality", 0.0)) - selected_quality
                if risk_reduction <= 0.03 and quality_gain <= 0.03:
                    continue
                move_score = (1.8 * risk_reduction + quality_gain) / max(extra_cost, 1)
                if best_move is None or move_score > best_move[0]:
                    best_move = (move_score, prompt_index, candidate, extra_cost)
        if best_move is not None:
            _score, prompt_index, candidate, extra_cost = best_move
            current[prompt_index] = candidate
            used_units += extra_cost
            improved = True
    return current


def _minimum_under_route(
    prompt_ids: list[str],
    prompt_options: list[list[dict]],
    expected_by_prompt: dict[str, str],
    budget_units: int,
) -> int:
    states: dict[int, int] = {0: 0}
    for prompt_id, options in zip(prompt_ids, prompt_options):
        expected = expected_by_prompt[prompt_id]
        next_states: dict[int, int] = {}
        for used_cost, under_count in states.items():
            for option in options:
                if expected != "abstain" and option["model_id"] == "abstain":
                    continue
                new_cost = used_cost + int(option["cost_units"])
                if new_cost > budget_units:
                    continue
                new_under = under_count + (1 if _classify(expected, option["model_id"]) == "under_route" else 0)
                current = next_states.get(new_cost)
                if current is None or new_under < current:
                    next_states[new_cost] = new_under
        states = next_states
        if not states:
            return len(prompt_ids)
    return min(states.values())


def _classify(expected: str, selected: str) -> str:
    if expected == selected:
        return "ok"
    if expected == "abstain":
        return "should_abstain"
    if selected == "abstain":
        return "under_route"
    if MODEL_RANK[selected] < MODEL_RANK[expected]:
        return "under_route"
    return "over_route"


