from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from router_impls.geometric.router import GeometricRouter


class RouterSubmission:
    """Private-simulator facing adapter.

    The challenge simulator can instantiate this class once, then call
    `route(...)` for each prompt. The adapter does not call external APIs; it
    only returns a local routing action.
    """

    def __init__(self, artifact_path: str | Path = "artifacts/geometric_router.json"):
        self.router = GeometricRouter.load(artifact_path)

    def route(
        self,
        prompt: str,
        budget_tier: str,
        history: list[dict[str, Any]] | None = None,
        model_metadata: list[dict[str, Any]] | None = None,
        task_type: str = "",
        difficulty: str = "",
        risk_level: str = "",
        evaluation_type: str = "",
    ) -> dict[str, Any]:
        del history, model_metadata
        decision = self.router.route(
            prompt=prompt,
            budget_tier=budget_tier,
            task_type=task_type,
            difficulty=difficulty,
            risk_level=risk_level,
            evaluation_type=evaluation_type,
        )
        if decision.selected_model_id == "abstain":
            action = {"type": "abstain", "model_id": None}
        else:
            action = {"type": "call_model", "model_id": decision.selected_model_id}
        return {
            "action": action,
            "selected_model_id": decision.selected_model_id,
            "selection_reason": decision.selection_reason,
            "diagnostics": asdict(decision),
        }


def create_router(artifact_path: str | Path = "artifacts/geometric_router.json") -> RouterSubmission:
    return RouterSubmission(artifact_path)


