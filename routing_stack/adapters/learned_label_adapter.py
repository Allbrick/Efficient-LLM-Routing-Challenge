from __future__ import annotations

from pathlib import Path

from routing_stack.adapters.contract import Candidate, RouteRequest, RouteResult
from routing_stack.training.prompt_label_model import LABELS, PromptLabelRouterModel


class LearnedLabelRouterAdapter:
    name = "learned_label"

    def __init__(self, artifact_path: str | Path = "artifacts/prompt_label_router.joblib"):
        self.artifact_path = str(artifact_path)
        self.model = PromptLabelRouterModel.load(artifact_path)

    def route(self, request: RouteRequest) -> RouteResult:
        prediction = self.model.predict(request.prompt)
        candidates = [
            Candidate(
                model_id=label,
                score=prediction.probabilities.get(label, 0.0),
                cost=_cost(label),
                feasible=True,
                reason="learned_label_probability",
                metrics={"label_probability": prediction.probabilities.get(label, 0.0)},
            )
            for label in LABELS
        ]
        return RouteResult(
            router_name=self.name,
            selected_model_id=prediction.selected_label,
            action_type="call_model",
            selection_reason="learned_label_probability",
            candidates=candidates,
            diagnostics={
                "artifact_path": self.artifact_path,
                "input_features": request.input_features,
                "context_features": request.context_features,
                "probabilities": prediction.probabilities,
            },
        )


def _cost(label: str) -> float:
    return {"cheap": 0.01, "mid": 0.05, "premium": 0.2}.get(label, 0.0)
