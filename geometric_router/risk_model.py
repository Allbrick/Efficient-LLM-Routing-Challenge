from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from geometric_router.features import MODEL_ORDER, MODEL_RANK, ROUTE_ACTIONS
from geometric_router.task_classifier import hashed_char_ngrams


TEXT_FEATURES = 256


@dataclass
class RiskExemplar:
    prompt_id: str
    feature: list[float]
    expected_min_model: str


@dataclass
class SufficiencyRiskModel:
    exemplars: list[RiskExemplar]
    bandwidth: float = 1.15

    def predict_expected_distribution(self, x: np.ndarray, prompt: str = "") -> dict[str, float]:
        query = _risk_vector(x, prompt)
        weights_by_model = {action: 0.0 for action in ROUTE_ACTIONS}
        total = 0.0
        for item in self.exemplars:
            diff = query - np.array(item.feature, dtype=np.float64)
            dist = float(np.linalg.norm(diff))
            weight = float(np.exp(-(dist * dist) / (2.0 * self.bandwidth * self.bandwidth)))
            if item.expected_min_model not in weights_by_model:
                continue
            weights_by_model[item.expected_min_model] += weight
            total += weight

        if total <= 1e-12:
            uniform = 1.0 / len(ROUTE_ACTIONS)
            return {action: uniform for action in ROUTE_ACTIONS}
        return {model: value / total for model, value in weights_by_model.items()}

    def sufficiency_probability(self, x: np.ndarray, model_id: str, prompt: str = "") -> float:
        distribution = self.predict_expected_distribution(x, prompt)
        if model_id == "abstain":
            return float(distribution.get("abstain", 0.0))
        selected_rank = MODEL_RANK[model_id]
        return float(
            sum(
                probability
                for expected_model, probability in distribution.items()
                if expected_model in MODEL_RANK and MODEL_RANK[expected_model] <= selected_rank
            )
        )

    def predict_all(self, x: np.ndarray, prompt: str = "") -> dict[str, float]:
        return {action: self.sufficiency_probability(x, action, prompt) for action in ROUTE_ACTIONS}

    def to_dict(self) -> dict:
        return {
            "bandwidth": self.bandwidth,
            "exemplars": [
                {
                    "prompt_id": item.prompt_id,
                    "feature": item.feature,
                    "expected_min_model": item.expected_min_model,
                }
                for item in self.exemplars
            ],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "SufficiencyRiskModel":
        return cls(
            bandwidth=float(payload.get("bandwidth", 1.15)),
            exemplars=[
                RiskExemplar(
                    prompt_id=str(item["prompt_id"]),
                    feature=[float(value) for value in item["feature"]],
                    expected_min_model=str(item["expected_min_model"]),
                )
                for item in payload.get("exemplars", [])
            ],
        )


def fit_risk_model(prompt_features: dict[str, np.ndarray], labels, prompt_texts: dict[str, str]) -> SufficiencyRiskModel:
    prompt_labels = labels.drop_duplicates("prompt_id")
    exemplars = []
    for row in prompt_labels.itertuples(index=False):
        prompt_id = str(row.prompt_id)
        exemplars.append(
            RiskExemplar(
                prompt_id=prompt_id,
                feature=_risk_vector(prompt_features[prompt_id], prompt_texts.get(prompt_id, "")).astype(float).tolist(),
                expected_min_model=str(row.expected_min_model),
            )
        )
    return SufficiencyRiskModel(exemplars=exemplars)


def _risk_vector(evidence_vector: np.ndarray, prompt: str) -> np.ndarray:
    text_vector = hashed_char_ngrams(prompt, n_features=TEXT_FEATURES)
    return np.concatenate([evidence_vector.astype(np.float64), text_vector.astype(np.float64)])
