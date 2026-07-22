from __future__ import annotations

from pathlib import Path

from routing_stack.adapters.contract import Candidate, RouteRequest, RouteResult
from routing_stack.training.prompt_label_model import MODEL_SLOTS, PromptLabelRouterModel


class LearnedLabelRouterAdapter:
    name = "learned_label"

    def __init__(self, artifact_path: str | Path = "artifacts/prompt_label_router.joblib"):
        self.artifact_path = str(artifact_path)
        self.model = PromptLabelRouterModel.load(artifact_path)

    def route(self, request: RouteRequest) -> RouteResult:
        prediction = self.model.predict(request.prompt)
        candidates = [
            Candidate(
                model_id=model_id,
                score=prediction.bucket_scores.get(model_id, 0.0),
                cost=_cost(model_id),
                feasible=True,
                reason="learned_routing_score_bucket",
                metrics={
                    "routing_score": prediction.routing_score,
                    "raw_routing_score": prediction.raw_routing_score,
                    "bucket_score": prediction.bucket_scores.get(model_id, 0.0),
                    "raw_bucket_score": prediction.raw_bucket_scores.get(model_id, 0.0),
                    "centroid_distance": prediction.geometry.get("centroid_distances", {}).get(model_id),
                    "centroid_probability": prediction.geometry.get("centroid_probabilities", {}).get(model_id),
                },
            )
            for model_id in MODEL_SLOTS
        ]
        return RouteResult(
            router_name=self.name,
            selected_model_id=prediction.selected_model_id,
            action_type="call_model",
            selection_reason="learned_routing_score",
            candidates=candidates,
            diagnostics={
                "artifact_path": self.artifact_path,
                "input_features": request.input_features,
                "context_features": request.context_features,
                "routing_score": prediction.routing_score,
                "raw_routing_score": prediction.raw_routing_score,
                "bucket_scores": prediction.bucket_scores,
                "raw_bucket_scores": prediction.raw_bucket_scores,
                "geometry": prediction.geometry,
            },
        )


def _cost(label: str) -> float:
    return {"cheap": 0.01, "mid": 0.05, "premium": 0.2}.get(label, 0.0)
