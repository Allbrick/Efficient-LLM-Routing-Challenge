from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from router_impls.geometric.evaluator import OutputEvaluator
from router_impls.geometric.features import MODEL_ORDER, MODEL_RANK
from router_impls.geometric.router import GeometricRouter


class RouterSubmission:
    """Private-simulator facing adapter.

    The challenge simulator can instantiate this class once, then call
    `route(...)` for each prompt. The adapter does not call external APIs; it
    only returns a local routing action.
    """

    def __init__(self, artifact_path: str | Path = "artifacts/geometric_router.json"):
        self.router = GeometricRouter.load(artifact_path)
        self.evaluator = OutputEvaluator()

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
        reference_answer: str = "",
        test_spec: str = "",
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
        history = history or []
        spec = {
            "evaluation_type": evaluation_type,
            "reference_answer": reference_answer,
            "test_spec": test_spec,
        }
        if decision.selected_model_id == "abstain":
            action = {"type": "abstain", "model_id": None}
        else:
            reusable = self._select_reusable_history(
                decision.selected_model_id,
                history,
                spec,
            )
            if reusable is None:
                escalation_model = self._next_escalation_model(
                    decision.selected_model_id,
                    history,
                    budget_tier,
                    spec,
                )
                action = {"type": "call_model", "model_id": escalation_model}
            else:
                action = {
                    "type": "select_output",
                    "model_id": reusable["model_id"],
                    "history_index": reusable["history_index"],
                }
        return {
            "action": action,
            "selected_model_id": action.get("model_id") or decision.selected_model_id,
            "selection_reason": decision.selection_reason,
            "diagnostics": asdict(decision),
        }

    def _select_reusable_history(
        self,
        selected_model_id: str,
        history: list[dict[str, Any]],
        spec: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if selected_model_id not in MODEL_RANK:
            return None
        selected_rank = MODEL_RANK[selected_model_id]
        has_structured_spec = bool(
            spec
            and str(spec.get("evaluation_type") or "").strip()
            and (
                str(spec.get("reference_answer") or "").strip()
                or str(spec.get("test_spec") or "").strip()
                or str(spec.get("evaluation_type") or "").strip() in {"required_clarification", "refusal_check"}
            )
        )
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
            if model_id not in MODEL_RANK:
                continue
            output = item.get("output")
            if output is None and "response" in item:
                output = item.get("response")
            if output is None and "model_output" in item:
                output = item.get("model_output")
            if output in {None, ""} and not bool(item.get("success") or item.get("sufficient")):
                continue
            explicit_success = bool(item.get("success") or item.get("sufficient"))
            evaluated_success = False
            evaluated_score = 0.0
            if output not in {None, ""} and has_structured_spec:
                sufficiency = self.evaluator.assess_sufficiency(
                    str(output),
                    spec,
                    item.get("quality_score") if "quality_score" in item else item.get("success_score"),
                )
                evaluated_success = bool(sufficiency.sufficient)
                evaluated_score = float(sufficiency.score)
            if has_structured_spec and not explicit_success and not evaluated_success:
                continue
            if MODEL_RANK[model_id] < selected_rank and not (explicit_success or evaluated_success):
                continue
            reusable.append(
                {
                    "model_id": model_id,
                    "history_index": int(item.get("history_index", index)),
                    "rank": MODEL_RANK[model_id],
                    "success": explicit_success or evaluated_success,
                    "score": evaluated_score,
                }
            )
        if not reusable:
            return None
        reusable.sort(key=lambda item: (not item["success"], item["rank"], -item["score"], item["history_index"]))
        return reusable[0]

    def _next_escalation_model(
        self,
        selected_model_id: str,
        history: list[dict[str, Any]],
        budget_tier: str,
        spec: dict[str, Any] | None = None,
    ) -> str:
        if selected_model_id not in MODEL_RANK:
            return selected_model_id
        if not self._selected_model_failed(selected_model_id, history, spec):
            return selected_model_id

        selected_rank = MODEL_RANK[selected_model_id]
        max_rank = 2
        tier = str(budget_tier or "balanced").lower()
        if tier == "fast":
            max_rank = max(selected_rank + 1, MODEL_RANK["mid"])
        for candidate in MODEL_ORDER[selected_rank + 1 : max_rank + 1]:
            if not self._model_has_failed(candidate, history, spec):
                return candidate
        return selected_model_id

    def _selected_model_failed(
        self,
        selected_model_id: str,
        history: list[dict[str, Any]],
        spec: dict[str, Any] | None = None,
    ) -> bool:
        return self._model_has_failed(selected_model_id, history, spec)

    def _model_has_failed(
        self,
        model_id: str,
        history: list[dict[str, Any]],
        spec: dict[str, Any] | None = None,
    ) -> bool:
        has_structured_spec = bool(
            spec
            and str(spec.get("evaluation_type") or "").strip()
            and (
                str(spec.get("reference_answer") or "").strip()
                or str(spec.get("test_spec") or "").strip()
                or str(spec.get("evaluation_type") or "").strip() in {"required_clarification", "refusal_check"}
            )
        )
        if not has_structured_spec:
            return False
        for item in history:
            if not isinstance(item, dict):
                continue
            item_model = str(
                item.get("model_id")
                or item.get("selected_model_id")
                or item.get("model_slot")
                or ""
            )
            if item_model != model_id:
                continue
            output = item.get("output")
            if output is None and "response" in item:
                output = item.get("response")
            if output is None and "model_output" in item:
                output = item.get("model_output")
            if output in {None, ""}:
                continue
            sufficiency = self.evaluator.assess_sufficiency(
                str(output),
                spec,
                item.get("quality_score") if "quality_score" in item else item.get("success_score"),
            )
            if sufficiency.sufficient:
                return False
            return True
        return False


def create_router(artifact_path: str | Path = "artifacts/geometric_router.json") -> RouterSubmission:
    return RouterSubmission(artifact_path)


