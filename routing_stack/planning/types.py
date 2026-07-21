from __future__ import annotations

from dataclasses import asdict, dataclass, field

from typing import Any

from routing_stack.adapters.contract import Candidate, RouteResult


MODEL_IDS = ("cheap", "mid", "premium")


@dataclass(frozen=True)
class RouterObservation:
    router_name: str
    selected_model_id: str
    selection_reason: str
    model_quality: dict[str, float | None]
    model_utility: dict[str, float | None]
    model_cost: dict[str, float | None]
    raw_result: RouteResult

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["raw_result"] = self.raw_result.to_dict()
        return payload


@dataclass(frozen=True)
class GeometricSignals:
    available: bool
    selected_model_id: str | None = None
    selection_reason: str | None = None
    simple_prompt_prior: bool = False
    frontier_model_id: str | None = None
    model_distance: dict[str, float | None] = field(default_factory=dict)
    normalized_distance: dict[str, float | None] = field(default_factory=dict)
    pass_probability: dict[str, float | None] = field(default_factory=dict)
    sufficiency_probability: dict[str, float | None] = field(default_factory=dict)
    feasible: dict[str, bool] = field(default_factory=dict)
    signals: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class UncertaintySignal:
    uncertain: bool
    confidence: float
    reason: str
    signals: dict[str, bool]
    metrics: dict[str, float]

    def to_dict(self) -> dict:
        return asdict(self)


def observation_from_result(result: RouteResult) -> RouterObservation:
    """RouteResult를 planning 계층의 표준 관측값으로 변환합니다."""
    return RouterObservation(
        router_name=result.router_name,
        selected_model_id=result.selected_model_id,
        selection_reason=result.selection_reason,
        model_quality={
            candidate.model_id: candidate_quality(candidate)
            for candidate in result.candidates
            if candidate.model_id != "abstain"
        },
        model_utility={
            candidate.model_id: _as_float(candidate.score)
            for candidate in result.candidates
            if candidate.model_id != "abstain"
        },
        model_cost={
            candidate.model_id: _as_float(candidate.cost)
            for candidate in result.candidates
            if candidate.model_id != "abstain"
        },
        raw_result=result,
    )


def candidate_quality(candidate: Candidate) -> float | None:
    """라우터별 metric 차이를 흡수해서 모델 품질 값을 하나로 읽습니다."""
    metrics = candidate.metrics or {}
    for key in ("policy_quality", "calibrated_quality", "predicted_quality", "pass_probability"):
        if key in metrics:
            return _as_float(metrics[key])
    return _as_float(candidate.score)


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
