from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from router_impls.geometric.evaluator import OutputEvaluator
from router_impls.geometric.features import MODEL_ORDER, MODEL_RANK
from router_impls.geometric.router import BUDGET_LIMITS, GeometricRouter, within_budget

DEFAULT_ARTIFACT_PATH = "artifacts/geometric_router.json"
DEFAULT_BUDGET_TIER = "balanced"
FALLBACK_MODEL_ID = "cheap"
_REPO_ROOT = Path(__file__).resolve().parents[2]

_TIER_ALIASES = {
    "fast": "fast",
    "cheap": "fast",
    "low": "fast",
    "economy": "fast",
    "balanced": "balanced",
    "standard": "balanced",
    "medium": "balanced",
    "mid": "balanced",
    "premium": "premium",
    "high": "premium",
    "quality": "premium",
}


def resolve_artifact_path(artifact_path: str | Path = DEFAULT_ARTIFACT_PATH) -> Path:
    """Resolve the router artifact regardless of the caller's working directory.

    The private simulator may import this module from any CWD, so a relative
    path is also looked up against the repository root.
    """
    candidate = Path(artifact_path)
    if candidate.is_file():
        return candidate
    if not candidate.is_absolute():
        repo_candidate = _REPO_ROOT / candidate
        if repo_candidate.is_file():
            return repo_candidate
    return candidate


def normalize_budget_tier(budget_tier: Any) -> str:
    """Map an arbitrary tier label onto a known tier without raising."""
    tier = str(budget_tier or "").strip().lower()
    if tier in BUDGET_LIMITS:
        return tier
    return _TIER_ALIASES.get(tier, DEFAULT_BUDGET_TIER)


class RouterSubmission:
    """Private-simulator facing adapter.

    The challenge simulator can instantiate this class once, then call
    `route(...)` for each prompt. The adapter does not call external APIs; it
    only returns a local routing action.
    """

    def __init__(self, artifact_path: str | Path = DEFAULT_ARTIFACT_PATH):
        self.artifact_path = resolve_artifact_path(artifact_path)
        self.router = GeometricRouter.load(self.artifact_path)
        self.evaluator = OutputEvaluator()

    def route(
        self,
        prompt: str,
        budget_tier: str = DEFAULT_BUDGET_TIER,
        history: list[dict[str, Any]] | None = None,
        model_metadata: list[dict[str, Any]] | None = None,
        task_type: str = "",
        difficulty: str = "",
        risk_level: str = "",
        evaluation_type: str = "",
        reference_answer: str = "",
        test_spec: str = "",
    ) -> dict[str, Any]:
        """Return a routing action, never raising to the simulator.

        Any unexpected input or internal failure degrades to the cheapest model
        call instead of aborting the whole evaluation run.
        """
        try:
            return self._route_impl(
                prompt=prompt,
                budget_tier=budget_tier,
                history=history,
                model_metadata=model_metadata,
                task_type=task_type,
                difficulty=difficulty,
                risk_level=risk_level,
                evaluation_type=evaluation_type,
                reference_answer=reference_answer,
                test_spec=test_spec,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            return self._fallback_response(exc)

    def _fallback_response(self, exc: Exception) -> dict[str, Any]:
        return {
            "action": {"type": "call_model", "model_id": FALLBACK_MODEL_ID},
            "selected_model_id": FALLBACK_MODEL_ID,
            "selection_reason": f"fallback_on_error:{type(exc).__name__}",
            "diagnostics": {"error": f"{type(exc).__name__}: {exc}"},
        }

    def _route_impl(
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
        prompt = "" if prompt is None else str(prompt)
        tier = normalize_budget_tier(budget_tier)
        history = _normalize_history(history)
        decision = self.router.route(
            prompt=prompt,
            budget_tier=tier,
            task_type=task_type,
            difficulty=difficulty,
            risk_level=risk_level,
            evaluation_type=evaluation_type,
            model_metadata=model_metadata,
        )
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
                    tier,
                    spec,
                )
                model_costs = self._request_model_costs(model_metadata)
                affordable = self._affordable_model(
                    escalation_model,
                    history,
                    tier,
                    model_costs,
                    spec,
                )
                if affordable is None:
                    # The remaining per-request budget cannot pay for any call.
                    # Reuse the best output already paid for, else abstain.
                    best = self._best_history_output(history, spec)
                    if best is None:
                        action = {"type": "abstain", "model_id": None}
                    else:
                        action = {
                            "type": "select_output",
                            "model_id": best["model_id"],
                            "history_index": best["history_index"],
                        }
                else:
                    action = {"type": "call_model", "model_id": affordable}
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

    def _request_model_costs(self, model_metadata: Any) -> dict[str, float]:
        costs = dict(self.router.model_costs)
        costs.update(self.router._model_costs_from_metadata(model_metadata))
        return costs

    def _spent_cost(self, history: list[dict[str, Any]], model_costs: dict[str, float]) -> float:
        """Cost already charged to this request by earlier model calls."""
        spent = 0.0
        for item in history:
            raw_cost = item.get("cost")
            if isinstance(raw_cost, (int, float)):
                spent += float(raw_cost)
                continue
            model_id = _history_model_id(item)
            if model_id in model_costs:
                spent += float(model_costs[model_id])
        return spent

    def _affordable_model(
        self,
        model_id: str,
        history: list[dict[str, Any]],
        tier: str,
        model_costs: dict[str, float],
        spec: dict[str, Any] | None = None,
    ) -> str | None:
        """Downgrade a planned call until it fits the remaining request budget.

        The budget is enforced per request, so previously spent cost counts
        against the tier limit before a new call is allowed. A model that
        already failed for this request is skipped: paying twice for the same
        output only burns budget.
        """
        limit = BUDGET_LIMITS[tier]
        remaining = limit - self._spent_cost(history, model_costs)
        if model_id not in MODEL_RANK:
            return model_id
        for candidate in reversed(MODEL_ORDER[: MODEL_RANK[model_id] + 1]):
            if not within_budget(float(model_costs.get(candidate, 0.0)), remaining):
                continue
            if self._model_has_failed(candidate, history, spec) or _explicitly_failed(candidate, history):
                continue
            return candidate
        return None

    def _best_history_output(
        self,
        history: list[dict[str, Any]],
        spec: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Best already-paid output, used when no further call is affordable."""
        best = None
        for index, item in enumerate(history):
            model_id = _history_model_id(item)
            if model_id not in MODEL_RANK:
                continue
            output = _history_output(item)
            if output in {None, ""}:
                continue
            candidate = {
                "model_id": model_id,
                "history_index": int(item.get("history_index", index)),
                "rank": MODEL_RANK[model_id],
            }
            if best is None or candidate["rank"] > best["rank"]:
                best = candidate
        return best

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
                    prompt="",
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
                prompt="",
            )
            if sufficiency.sufficient:
                return False
            return True
        return False


def _explicitly_failed(model_id: str, history: list[dict[str, Any]]) -> bool:
    """True when history marks this model's attempt as unsuccessful."""
    for item in history:
        if _history_model_id(item) != model_id:
            continue
        if item.get("success") is False or item.get("sufficient") is False:
            return True
    return False


def _history_model_id(item: dict[str, Any]) -> str:
    return str(
        item.get("model_id")
        or item.get("selected_model_id")
        or item.get("model_slot")
        or ""
    )


def _history_output(item: dict[str, Any]) -> Any:
    output = item.get("output")
    if output is None and "response" in item:
        output = item.get("response")
    if output is None and "model_output" in item:
        output = item.get("model_output")
    return output


def _normalize_history(history: Any) -> list[dict[str, Any]]:
    """Keep only dict-shaped history entries, tolerating any input shape.

    Dropping non-dict entries would shift positions, so each kept entry carries
    an explicit ``history_index`` pointing at its slot in the original list.
    """
    if not isinstance(history, (list, tuple)):
        return []
    normalized = []
    for index, item in enumerate(history):
        if not isinstance(item, dict):
            continue
        if "history_index" in item:
            normalized.append(item)
            continue
        entry = dict(item)
        entry["history_index"] = index
        normalized.append(entry)
    return normalized


def create_router(artifact_path: str | Path = DEFAULT_ARTIFACT_PATH) -> RouterSubmission:
    return RouterSubmission(artifact_path)


