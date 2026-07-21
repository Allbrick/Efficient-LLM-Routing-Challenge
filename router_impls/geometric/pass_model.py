from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from router_impls.geometric.features import MODEL_ORDER


@dataclass
class PassExemplar:
    prompt_id: str
    model_id: str
    feature: list[float]
    success: bool


@dataclass
class PassProbabilityModel:
    exemplars: list[PassExemplar]
    bandwidth: float = 1.25

    def predict_one(self, x: np.ndarray, model_id: str) -> float:
        model_examples = [item for item in self.exemplars if item.model_id == model_id]
        if not model_examples:
            return 0.0

        weights = []
        outcomes = []
        for item in model_examples:
            diff = x - np.array(item.feature, dtype=np.float64)
            dist = float(np.linalg.norm(diff))
            weight = float(np.exp(-(dist * dist) / (2.0 * self.bandwidth * self.bandwidth)))
            weights.append(weight)
            outcomes.append(1.0 if item.success else 0.0)

        total_weight = float(np.sum(weights))
        if total_weight <= 1e-12:
            return float(np.mean(outcomes))
        return float(np.dot(weights, outcomes) / total_weight)

    def predict_all(self, x: np.ndarray) -> dict[str, float]:
        return {model_id: self.predict_one(x, model_id) for model_id in MODEL_ORDER}

    def to_dict(self) -> dict:
        return {
            "bandwidth": self.bandwidth,
            "exemplars": [
                {
                    "prompt_id": item.prompt_id,
                    "model_id": item.model_id,
                    "feature": item.feature,
                    "success": item.success,
                }
                for item in self.exemplars
            ],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "PassProbabilityModel":
        return cls(
            bandwidth=float(payload.get("bandwidth", 1.25)),
            exemplars=[
                PassExemplar(
                    prompt_id=str(item["prompt_id"]),
                    model_id=str(item["model_id"]),
                    feature=[float(value) for value in item["feature"]],
                    success=bool(item["success"]),
                )
                for item in payload.get("exemplars", [])
            ],
        )


def fit_pass_model(prompt_features: dict[str, np.ndarray], labels) -> PassProbabilityModel:
    exemplars = []
    for row in labels.itertuples(index=False):
        feature = prompt_features[str(row.prompt_id)]
        exemplars.append(
            PassExemplar(
                prompt_id=str(row.prompt_id),
                model_id=str(row.model_id),
                feature=feature.astype(float).tolist(),
                success=bool(row.success),
            )
        )
    return PassProbabilityModel(exemplars=exemplars)


