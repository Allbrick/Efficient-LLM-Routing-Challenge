from __future__ import annotations

from typing import Any

from routing_stack.adapters.contract import RouteResult
from routing_stack.planning.types import MODEL_IDS, GeometricSignals


def extract_geometric_signals(result: RouteResult | None) -> GeometricSignals:
    if result is None or result.router_name != "geometric":
        return GeometricSignals(available=False)

    evidence = dict(result.diagnostics.get("evidence") or {})
    frontier_hint = result.diagnostics.get("frontier_hint") or {}
    simple_prompt_prior = bool(float(evidence.get("simple_prompt_prior", 0.0) or 0.0) >= 1.0)

    model_distance = _empty_float_map()
    normalized_distance = _empty_float_map()
    pass_probability = _empty_float_map()
    sufficiency_probability = _empty_float_map()
    feasible = {model_id: False for model_id in MODEL_IDS}

    for candidate in result.candidates:
        if candidate.model_id not in MODEL_IDS:
            continue
        metrics = candidate.metrics or {}
        model_distance[candidate.model_id] = _as_float(metrics.get("distance"))
        normalized_distance[candidate.model_id] = _as_float(metrics.get("normalized_distance"))
        pass_probability[candidate.model_id] = _as_float(metrics.get("pass_probability"))
        sufficiency_probability[candidate.model_id] = _as_float(metrics.get("sufficiency_probability"))
        feasible[candidate.model_id] = bool(metrics.get("feasible", candidate.feasible))

    signals = {
        "cheap_geometrically_safe": _is_cheap_safe(feasible, pass_probability, simple_prompt_prior),
        "mid_geometrically_safe": _is_mid_safe(feasible, pass_probability),
        "only_premium_near": _is_only_premium_near(normalized_distance),
        "all_envelopes_far": _are_all_envelopes_far(normalized_distance),
        "high_under_route_risk": _is_high_under_route_risk(sufficiency_probability),
    }

    return GeometricSignals(
        available=True,
        selected_model_id=result.selected_model_id,
        selection_reason=result.selection_reason,
        simple_prompt_prior=simple_prompt_prior,
        frontier_model_id=_as_str(frontier_hint.get("model_id")),
        model_distance=model_distance,
        normalized_distance=normalized_distance,
        pass_probability=pass_probability,
        sufficiency_probability=sufficiency_probability,
        feasible=feasible,
        signals=signals,
    )


def _empty_float_map() -> dict[str, float | None]:
    return {model_id: None for model_id in MODEL_IDS}


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _is_cheap_safe(feasible: dict[str, bool], pass_probability: dict[str, float | None], simple_prompt_prior: bool) -> bool:
    return bool(feasible.get("cheap") or (pass_probability.get("cheap") or 0.0) >= 0.74 or simple_prompt_prior)


def _is_mid_safe(feasible: dict[str, bool], pass_probability: dict[str, float | None]) -> bool:
    return bool(feasible.get("mid") or (pass_probability.get("mid") or 0.0) >= 0.82)


def _is_only_premium_near(normalized_distance: dict[str, float | None]) -> bool:
    cheap = normalized_distance.get("cheap")
    mid = normalized_distance.get("mid")
    premium = normalized_distance.get("premium")
    if cheap is None or mid is None or premium is None:
        return False
    return premium <= 1.25 and cheap >= 2.0 and mid >= 1.6


def _are_all_envelopes_far(normalized_distance: dict[str, float | None]) -> bool:
    values = [value for value in normalized_distance.values() if value is not None]
    return bool(values) and min(values) >= 2.5


def _is_high_under_route_risk(sufficiency_probability: dict[str, float | None]) -> bool:
    cheap = sufficiency_probability.get("cheap")
    mid = sufficiency_probability.get("mid")
    return (cheap is not None and cheap < 0.45) and (mid is not None and mid < 0.65)
