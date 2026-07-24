from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from router_impls.geometric.features import MODEL_RANK
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
        decision = self.router.route(
            prompt=prompt,
            budget_tier=budget_tier,
            task_type=task_type,
            difficulty=difficulty,
            risk_level=risk_level,
            evaluation_type=evaluation_type,
            model_metadata=model_metadata,
        )
        if decision.selected_model_id == "abstain":
            action = {"type": "abstain", "model_id": None}
        else:
            reusable = self._select_reusable_history(decision.selected_model_id, history or [])
            if reusable is None:
                action = {"type": "call_model", "model_id": decision.selected_model_id}
            else:
                action = {
                    "type": "select_output",
                    "model_id": reusable["model_id"],
                    "history_index": reusable["history_index"],
                }
        return {
            "action": action,
            "selected_model_id": decision.selected_model_id,
            "selection_reason": decision.selection_reason,
            "diagnostics": asdict(decision),
        }

    def _select_reusable_history(self, selected_model_id: str, history: list[dict[str, Any]]) -> dict[str, Any] | None:
        if selected_model_id not in MODEL_RANK:
            return None
        selected_rank = MODEL_RANK[selected_model_id]
        reusable = []
        for index, item in enumerate(history):
            if not isinstance(item, dict):
                continue
            model_id = str(
                item.get("model_id")
                or item.get("selected_model_id")
                or item.get("model_slot")
                or ""
            )
            if model_id not in MODEL_RANK or MODEL_RANK[model_id] < selected_rank:
                continue
            output = item.get("output")
            if output is None and "response" in item:
                output = item.get("response")
            if output is None and "model_output" in item:
                output = item.get("model_output")
            if output in {None, ""} and not bool(item.get("success") or item.get("sufficient")):
                continue
            reusable.append(
                {
                    "model_id": model_id,
                    "history_index": int(item.get("history_index", index)),
                    "rank": MODEL_RANK[model_id],
                    "success": bool(item.get("success") or item.get("sufficient")),
                }
            )
        if not reusable:
            return None
        reusable.sort(key=lambda item: (not item["success"], item["rank"], item["history_index"]))
        return reusable[0]


def create_router(artifact_path: str | Path = "artifacts/geometric_router.json") -> RouterSubmission:
    return RouterSubmission(artifact_path)


