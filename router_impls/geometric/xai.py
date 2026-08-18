from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from router_impls.geometric.envelope import Envelope


EVIDENCE_FEATURE_NAMES = [
    "difficulty_score",
    "risk_score",
    "condition_count",
    "missing_context",
    "exact_answer",
    "code_like",
    "length_norm",
    "line_norm",
    "eval_type_id",
    "char_ngram_0",
    "char_ngram_1",
    "char_ngram_2",
    "char_ngram_3",
    "char_ngram_4",
    "char_ngram_5",
    "char_ngram_6",
    "char_ngram_7",
    "char_ngram_8",
    "char_ngram_9",
    "char_ngram_10",
    "char_ngram_11",
    "char_ngram_12",
    "char_ngram_13",
    "char_ngram_14",
    "char_ngram_15",
    "token_count_norm",
    "estimated_input_tokens_norm",
    "estimated_output_tokens_norm",
    "cost_estimate_norm",
    "code_token_pressure",
    "json_or_table_pressure",
    "difficulty_risk_interaction",
    "code_complexity_interaction",
    "cost_pressure_interaction",
]


@dataclass
class FeatureContribution:
    model_id: str
    total_distance_squared: float
    total_distance: float
    contributions: dict[str, float]
    top_pushing_away: list[tuple[str, float]]
    top_pulling_toward: list[tuple[str, float]]


def decompose_mahalanobis(
    x: np.ndarray,
    envelope: Envelope,
    feature_names: list[str] | None = None,
    top_k: int = 5,
) -> FeatureContribution:
    mean = np.array(envelope.mean, dtype=np.float64)
    inv_cov = np.array(envelope.inverse_covariance, dtype=np.float64)

    dim = len(mean)
    if feature_names is None:
        feature_names = [f"feature_{i}" for i in range(dim)]
    if len(feature_names) < dim:
        feature_names = list(feature_names) + [f"feature_{i}" for i in range(len(feature_names), dim)]

    delta = x.astype(np.float64) - mean
    inv_delta = inv_cov @ delta

    contributions_array = delta * inv_delta
    d_squared = float(np.sum(contributions_array))
    d_squared = max(d_squared, 0.0)
    d = float(np.sqrt(d_squared))

    contributions = {}
    for i in range(dim):
        contributions[feature_names[i]] = float(contributions_array[i])

    sorted_items = sorted(contributions.items(), key=lambda item: item[1])
    top_pulling = [(name, val) for name, val in sorted_items if val < 0][:top_k]
    top_pushing = [(name, val) for name, val in sorted_items[::-1] if val > 0][:top_k]

    return FeatureContribution(
        model_id=envelope.model_id,
        total_distance_squared=d_squared,
        total_distance=d,
        contributions=contributions,
        top_pushing_away=top_pushing,
        top_pulling_toward=top_pulling,
    )


def decompose_all_models(
    x: np.ndarray,
    envelopes: dict[str, Envelope],
    feature_names: list[str] | None = None,
    top_k: int = 5,
) -> dict[str, FeatureContribution]:
    return {
        model_id: decompose_mahalanobis(x, envelope, feature_names, top_k)
        for model_id, envelope in envelopes.items()
    }


def contributions_to_evidence(
    contributions: dict[str, FeatureContribution],
) -> dict[str, float]:
    result: dict[str, float] = {}
    for model_id, fc in contributions.items():
        result[f"xai_{model_id}_distance"] = fc.total_distance
        result[f"xai_{model_id}_distance_squared"] = fc.total_distance_squared
        for name, val in fc.top_pushing_away:
            key = f"xai_{model_id}_push_{name}"
            result[key] = val
        for name, val in fc.top_pulling_toward:
            key = f"xai_{model_id}_pull_{name}"
            result[key] = val
    return result
