from __future__ import annotations

from routing_stack.planning.types import MODEL_IDS, GeometricSignals, RouterObservation, UncertaintySignal


def assess_uncertainty(
    observations: list[RouterObservation],
    input_features: dict,
    tier: str,
    geometric_signals: GeometricSignals | None = None,
) -> UncertaintySignal:
    tier_lower = str(tier or "balanced").lower()
    selected = [obs.selected_model_id for obs in observations]
    router_disagreement = len(set(selected)) > 1
    quality_margin = _minimum_quality_margin(observations)
    selected_quality = _mean_selected_quality(observations)
    cost_pressure = _cost_pressure(input_features, tier_lower)
    high_premium_gap = _high_premium_gap(observations)
    missing_context = bool(input_features.get("missing_context", False))

    geo = geometric_signals or GeometricSignals(available=False)
    geometric_out_of_distribution = bool(geo.signals.get("all_envelopes_far", False))
    geometric_cheap_safe = bool(geo.signals.get("cheap_geometrically_safe", False))
    geometric_only_premium_near = bool(geo.signals.get("only_premium_near", False))

    signals = {
        "router_disagreement": router_disagreement,
        "small_quality_margin": quality_margin < 0.08,
        "low_selected_quality": selected_quality < 0.55,
        "high_cost_pressure": cost_pressure >= 0.65,
        "missing_context": missing_context,
        "high_premium_gap": high_premium_gap,
        "geometric_out_of_distribution": geometric_out_of_distribution,
        "geometric_cheap_safe": geometric_cheap_safe,
        "geometric_only_premium_near": geometric_only_premium_near,
    }

    confidence = 1.0
    if signals["router_disagreement"]:
        confidence -= 0.35
    if signals["small_quality_margin"]:
        confidence -= 0.20
    if signals["low_selected_quality"]:
        confidence -= 0.15
    if signals["high_cost_pressure"]:
        confidence -= 0.15
    if signals["missing_context"]:
        confidence -= 0.20
    if signals["geometric_out_of_distribution"]:
        confidence -= 0.15
    if signals["geometric_cheap_safe"] and tier_lower == "fast":
        confidence += 0.10

    confidence = max(0.0, min(1.0, confidence))
    threshold = 0.78 if tier_lower == "fast" else 0.70
    uncertain = confidence < threshold
    reason = _primary_reason(signals) if uncertain else "confident"

    return UncertaintySignal(
        uncertain=uncertain,
        confidence=round(confidence, 6),
        reason=reason,
        signals=signals,
        metrics={
            "quality_margin": round(quality_margin, 6),
            "cost_pressure": round(cost_pressure, 6),
            "selected_quality": round(selected_quality, 6),
        },
    )


def _minimum_quality_margin(observations: list[RouterObservation]) -> float:
    margins = [_quality_margin(obs.model_quality) for obs in observations]
    values = [value for value in margins if value is not None]
    return min(values) if values else 0.0


def _quality_margin(qualities: dict[str, float | None]) -> float | None:
    values = [value for model_id, value in qualities.items() if model_id in MODEL_IDS and value is not None]
    if len(values) < 2:
        return None
    low = min(values)
    high = max(values)
    if abs(high - low) <= 1e-12:
        return 0.0
    normalized = sorted(((value - low) / (high - low) for value in values), reverse=True)
    raw = sorted(values, reverse=True)
    return float(min(normalized[0] - normalized[1], raw[0] - raw[1]))


def _mean_selected_quality(observations: list[RouterObservation]) -> float:
    values = []
    for obs in observations:
        quality = obs.model_quality.get(obs.selected_model_id)
        if quality is not None:
            values.append(float(quality))
    if not values:
        return 0.0
    return sum(values) / len(values)


def _cost_pressure(input_features: dict, tier: str) -> float:
    input_tokens = float(input_features.get("estimated_input_tokens", 0.0) or 0.0)
    output_tokens = float(input_features.get("estimated_output_tokens", 0.0) or 0.0)
    code_pressure = float(input_features.get("code_token_pressure", 0.0) or 0.0)
    table_pressure = float(input_features.get("json_or_table_pressure", 0.0) or 0.0)
    input_limit = 700.0 if tier == "fast" else 1200.0
    output_limit = 900.0 if tier == "fast" else 1600.0
    token_pressure = max(input_tokens / input_limit, output_tokens / output_limit)
    return max(0.0, min(1.0, max(token_pressure, code_pressure, table_pressure)))


def _high_premium_gap(observations: list[RouterObservation]) -> bool:
    for obs in observations:
        cheap = obs.model_quality.get("cheap")
        premium = obs.model_quality.get("premium")
        if cheap is not None and premium is not None and premium - cheap >= 0.25:
            return True
    return False


def _primary_reason(signals: dict[str, bool]) -> str:
    for key in (
        "missing_context",
        "router_disagreement",
        "geometric_out_of_distribution",
        "small_quality_margin",
        "high_cost_pressure",
        "low_selected_quality",
    ):
        if signals.get(key):
            return key
    return "uncertain"
