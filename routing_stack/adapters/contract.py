from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


MODEL_SLOTS = ("cheap", "mid", "premium")


@dataclass
class RouteRequest:
    prompt: str
    tier: str = "balanced"
    task_type: str = ""
    difficulty: str = ""
    risk_level: str = ""
    evaluation_type: str = ""


@dataclass
class Candidate:
    model_id: str
    score: float | None = None
    cost: float | None = None
    feasible: bool | None = None
    reason: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RouteResult:
    router_name: str
    selected_model_id: str
    action_type: str
    selection_reason: str
    candidates: list[Candidate] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    @property
    def model_slot(self) -> str | None:
        if self.action_type == "abstain" or self.selected_model_id == "abstain":
            return None
        return self.selected_model_id

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["model_slot"] = self.model_slot
        payload["candidates"] = [candidate.to_dict() for candidate in self.candidates]
        return payload


class RouterAdapter(Protocol):
    name: str

    def route(self, request: RouteRequest) -> RouteResult:
        ...

