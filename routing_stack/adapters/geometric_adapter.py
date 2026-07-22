from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from router_impls.geometric.router import GeometricRouter
from routing_stack.adapters.contract import Candidate, RouteRequest, RouteResult


class GeometricRouterAdapter:
    name = "geometric"

    def __init__(self, artifact_path: str | Path = "artifacts/geometric_router.json"):
        self.router = GeometricRouter.load(artifact_path)

    def route(self, request: RouteRequest) -> RouteResult:
        decision = self.router.route(
            prompt=request.prompt,
            budget_tier=request.tier,
            task_type=request.task_type,
            difficulty=request.difficulty,
            risk_level=request.risk_level,
            evaluation_type=request.evaluation_type,
        )
        candidates = []
        for item in decision.candidates:
            candidates.append(
                Candidate(
                    model_id=str(item["model_id"]),
                    score=float(item.get("pass_probability", 0.0)),
                    cost=float(item.get("cost", 0.0)),
                    feasible=bool(item.get("feasible", False)),
                    reason=str(item.get("action_type", "")),
                    metrics=dict(item),
                )
            )
        action_type = "abstain" if decision.selected_model_id == "abstain" else "call_model"
        diagnostics = asdict(decision)
        diagnostics["input_features"] = request.input_features
        diagnostics["context_features"] = request.context_features
        return RouteResult(
            router_name=self.name,
            selected_model_id=decision.selected_model_id,
            action_type=action_type,
            selection_reason=decision.selection_reason,
            candidates=candidates,
            diagnostics=diagnostics,
        )


