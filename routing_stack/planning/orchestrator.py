from __future__ import annotations

from routing_stack.adapters.contract import Candidate, RouteRequest, RouteResult
from routing_stack.planning.types import MODEL_IDS, GeometricSignals, RouterObservation, UncertaintySignal


def orchestrate_route(
    request: RouteRequest,
    observations: list[RouterObservation],
    uncertainty: UncertaintySignal,
    geometric_signals: GeometricSignals | None = None,
) -> RouteResult:
    if not observations:
        raise ValueError("observations_required")

    geo = geometric_signals or GeometricSignals(available=False)
    tier = str(request.tier or "balanced").lower()
    selected, reason = _select_model(request, observations, uncertainty, geo, tier)
    action_type = "abstain" if selected == "abstain" else "call_model"
    candidates = _merge_candidates(observations)
    if selected == "abstain" and not any(candidate.model_id == "abstain" for candidate in candidates):
        candidates.insert(0, Candidate(model_id="abstain", score=0.0, cost=0.0, feasible=True, reason="orchestrator"))

    return RouteResult(
        router_name="orchestrator",
        selected_model_id=selected,
        action_type=action_type,
        selection_reason=reason,
        candidates=candidates,
        diagnostics={
            "observations": [obs.to_dict() for obs in observations],
            "uncertainty": uncertainty.to_dict(),
            "geometric_signals": geo.to_dict(),
            "context_features": request.context_features,
            "policy": {"tier": tier, "rule": reason},
        },
    )


def _select_model(
    request: RouteRequest,
    observations: list[RouterObservation],
    uncertainty: UncertaintySignal,
    geo: GeometricSignals,
    tier: str,
) -> tuple[str, str]:
    features = request.input_features or {}
    context = request.context_features or {}
    combined = {**features, **context}
    if bool(context.get("missing_context", features.get("missing_context"))) or uncertainty.signals.get("reference_unresolved") or uncertainty.signals.get("missing_context"):
        return "abstain", "missing_context"
    if bool(features.get("simple_directive")) and not bool(context.get("requires_cross_turn_reasoning")):
        return "cheap", "simple_directive"
    if tier in {"balanced", "premium"} and bool(combined.get("advanced_reasoning_task")):
        return "premium", "advanced_reasoning_task"
    if tier == "balanced" and _task_prefers_mid(combined):
        return "mid", "balanced_task_complexity"
    if bool(context.get("previous_cheap_failure")) and tier in {"fast", "balanced"}:
        if tier == "fast":
            return "mid", "previous_cheap_failure"
        return _best_excluding(observations, "cheap"), "previous_cheap_failure"
    if bool(context.get("references_code")) and bool(context.get("has_resolved_reference")) and tier == "fast":
        pressure = float(context.get("context_token_pressure", 0.0) or 0.0)
        if pressure >= 0.25:
            return "mid", "resolved_code_context"
    if geo.signals.get("cheap_geometrically_safe") and (tier == "fast" or not _task_prefers_mid_or_higher(combined)):
        return "cheap", "cheap_geometrically_safe"

    votes = _vote_counts(observations)
    if not uncertainty.uncertain and len(votes) == 1:
        selected = next(iter(votes))
        return selected, "router_agreement"

    if tier == "fast":
        return _select_fast(observations, uncertainty, geo)
    if tier == "premium":
        return _select_premium(observations, uncertainty, geo)
    return _select_balanced(observations, uncertainty, geo)


def _select_fast(
    observations: list[RouterObservation],
    uncertainty: UncertaintySignal,
    geo: GeometricSignals,
) -> tuple[str, str]:
    best = _best_by_mean_utility(observations)
    cheap_quality = _mean_quality(observations, "cheap")
    allow_premium = (
        uncertainty.signals.get("high_premium_gap", False)
        and cheap_quality < 0.45
        and _vote_counts(observations).get("premium", 0) > 0
        and not geo.signals.get("cheap_geometrically_safe", False)
        and not uncertainty.signals.get("reference_unresolved", False)
    )
    if best == "premium" and not allow_premium:
        if geo.signals.get("mid_geometrically_safe"):
            return "mid", "fast_mid_geometrically_safe"
        return "cheap", "fast_premium_blocked"
    return best, "fast_utility"


def _select_balanced(
    observations: list[RouterObservation],
    uncertainty: UncertaintySignal,
    geo: GeometricSignals,
) -> tuple[str, str]:
    if geo.signals.get("mid_geometrically_safe") and _quality_gap(observations, "premium", "mid") < 0.12:
        return "mid", "mid_geometrically_safe"
    if _quality_gap(observations, "premium", "mid") < 0.08 and _best_by_mean_utility(observations) == "premium":
        return "mid", "balanced_small_premium_gap"
    if _quality_gap(observations, "mid", "cheap") < 0.08 and _best_by_mean_utility(observations) == "mid":
        return "cheap", "balanced_small_mid_gap"
    return _best_by_mean_utility(observations), "balanced_utility"


def _select_premium(
    observations: list[RouterObservation],
    uncertainty: UncertaintySignal,
    geo: GeometricSignals,
) -> tuple[str, str]:
    if uncertainty.signals.get("reference_unresolved") or uncertainty.signals.get("missing_context"):
        return "abstain", "missing_context"
    if uncertainty.signals.get("previous_failure") and uncertainty.signals.get("high_premium_gap"):
        return "premium", "premium_after_failure"
    if geo.signals.get("only_premium_near") and uncertainty.signals.get("high_premium_gap"):
        return "premium", "only_premium_near"
    if uncertainty.signals.get("high_premium_gap"):
        return "premium", "premium_quality_gap"
    best = _best_by_mean_quality(observations)
    if best == "premium" and _quality_gap(observations, "premium", "mid") < 0.08:
        return "mid", "premium_small_gap"
    return best, "premium_quality"


def _merge_candidates(observations: list[RouterObservation]) -> list[Candidate]:
    candidates = []
    votes = _vote_counts(observations)
    for model_id in MODEL_IDS:
        qualities = _values([obs.model_quality.get(model_id) for obs in observations])
        utilities = _values([obs.model_utility.get(model_id) for obs in observations])
        costs = _values([obs.model_cost.get(model_id) for obs in observations])
        selected_by = [obs.router_name for obs in observations if obs.selected_model_id == model_id]
        score = _mean(utilities) if utilities else _mean(qualities)
        candidates.append(
            Candidate(
                model_id=model_id,
                score=score,
                cost=min(costs) if costs else None,
                feasible=True,
                reason="orchestrated",
                metrics={
                    "mean_quality": _mean(qualities),
                    "max_quality": max(qualities) if qualities else None,
                    "mean_utility": _mean(utilities),
                    "min_cost": min(costs) if costs else None,
                    "router_votes": votes.get(model_id, 0),
                    "selected_by": selected_by,
                },
            )
        )
    return candidates


def _vote_counts(observations: list[RouterObservation]) -> dict[str, int]:
    counts = {}
    for obs in observations:
        counts[obs.selected_model_id] = counts.get(obs.selected_model_id, 0) + 1
    return counts


def _best_by_mean_utility(observations: list[RouterObservation]) -> str:
    scores = {model_id: _mean(_values([obs.model_utility.get(model_id) for obs in observations])) for model_id in MODEL_IDS}
    return max(scores, key=lambda model_id: (scores[model_id] if scores[model_id] is not None else float("-inf"), -_rank(model_id)))


def _best_by_mean_quality(observations: list[RouterObservation]) -> str:
    scores = {model_id: _mean(_values([obs.model_quality.get(model_id) for obs in observations])) for model_id in MODEL_IDS}
    return max(scores, key=lambda model_id: (scores[model_id] if scores[model_id] is not None else float("-inf"), -_rank(model_id)))


def _best_excluding(observations: list[RouterObservation], excluded: str) -> str:
    scores = {
        model_id: _mean(_values([obs.model_utility.get(model_id) for obs in observations]))
        for model_id in MODEL_IDS
        if model_id != excluded
    }
    return max(scores, key=lambda model_id: (scores[model_id] if scores[model_id] is not None else float("-inf"), -_rank(model_id)))


def _mean_quality(observations: list[RouterObservation], model_id: str) -> float:
    return _mean(_values([obs.model_quality.get(model_id) for obs in observations])) or 0.0


def _quality_gap(observations: list[RouterObservation], left: str, right: str) -> float:
    return _mean_quality(observations, left) - _mean_quality(observations, right)


def _values(values: list[float | None]) -> list[float]:
    return [float(value) for value in values if value is not None]


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _rank(model_id: str) -> int:
    return {"cheap": 0, "mid": 1, "premium": 2}.get(model_id, 99)


def _task_prefers_mid(features: dict) -> bool:
    return bool(
        features.get("technical_explanation")
        or features.get("comparison_task")
        or features.get("design_task")
        or features.get("references_code")
        or features.get("references_design")
        or float(features.get("task_complexity_hint", 0.0) or 0.0) >= 0.45
    )


def _task_prefers_mid_or_higher(features: dict) -> bool:
    return bool(_task_prefers_mid(features) or features.get("advanced_reasoning_task"))
