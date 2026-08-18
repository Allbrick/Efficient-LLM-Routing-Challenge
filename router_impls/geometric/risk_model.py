from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from router_impls.geometric.features import MODEL_ORDER, MODEL_RANK, ROUTE_ACTIONS
from router_impls.geometric.task_classifier import hashed_char_ngrams


TEXT_FEATURES = 256


@dataclass
class PCATransform:
    mean: list[float]
    components: list[list[float]]
    explained_variance_ratio: list[float]
    n_components: int

    def transform(self, x: np.ndarray) -> np.ndarray:
        centered = x.astype(np.float64) - np.array(self.mean, dtype=np.float64)
        W = np.array(self.components, dtype=np.float64)
        return centered @ W.T

    def to_dict(self) -> dict:
        return {
            "mean": self.mean,
            "components": self.components,
            "explained_variance_ratio": self.explained_variance_ratio,
            "n_components": self.n_components,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> PCATransform:
        return cls(
            mean=[float(v) for v in payload["mean"]],
            components=[[float(v) for v in row] for row in payload["components"]],
            explained_variance_ratio=[float(v) for v in payload["explained_variance_ratio"]],
            n_components=int(payload["n_components"]),
        )


def fit_pca_transform(
    vectors: np.ndarray,
    variance_threshold: float = 0.90,
    max_components: int | None = None,
) -> PCATransform:
    from sklearn.decomposition import PCA

    n_samples, n_features = vectors.shape
    n_max = min(n_samples, n_features)
    pca = PCA(n_components=n_max)
    pca.fit(vectors)

    cumulative = np.cumsum(pca.explained_variance_ratio_)
    n_components = int(np.searchsorted(cumulative, variance_threshold) + 1)
    n_components = min(n_components, n_max)
    if max_components is not None:
        n_components = min(n_components, max_components)
    n_components = max(n_components, 1)

    return PCATransform(
        mean=pca.mean_.tolist(),
        components=pca.components_[:n_components].tolist(),
        explained_variance_ratio=pca.explained_variance_ratio_[:n_components].tolist(),
        n_components=n_components,
    )


@dataclass
class RiskExemplar:
    prompt_id: str
    feature: list[float]
    expected_min_model: str


@dataclass
class SufficiencyRiskModel:
    exemplars: list[RiskExemplar]
    bandwidth: float = 1.15
    pca_transform: PCATransform | None = None

    def predict_expected_distribution(self, x: np.ndarray, prompt: str = "") -> dict[str, float]:
        query = _risk_vector(x, prompt)
        if self.pca_transform is not None:
            query = self.pca_transform.transform(query)
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
        result = {
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
        if self.pca_transform is not None:
            result["pca_transform"] = self.pca_transform.to_dict()
        return result

    @classmethod
    def from_dict(cls, payload: dict) -> "SufficiencyRiskModel":
        pca_transform = None
        if payload.get("pca_transform") is not None:
            pca_transform = PCATransform.from_dict(payload["pca_transform"])
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
            pca_transform=pca_transform,
        )


def fit_risk_model(
    prompt_features: dict[str, np.ndarray],
    labels,
    prompt_texts: dict[str, str],
    bandwidth: float = 1.15,
    use_pca: bool = False,
    pca_variance: float = 0.90,
) -> SufficiencyRiskModel:
    prompt_labels = labels.drop_duplicates("prompt_id")

    raw_vectors = {}
    for row in prompt_labels.itertuples(index=False):
        prompt_id = str(row.prompt_id)
        raw_vectors[prompt_id] = _risk_vector(
            prompt_features[prompt_id], prompt_texts.get(prompt_id, "")
        ).astype(np.float64)

    pca_transform = None
    if use_pca and raw_vectors:
        all_vectors = np.array(list(raw_vectors.values()), dtype=np.float64)
        if all_vectors.shape[0] > 1:
            pca_transform = fit_pca_transform(all_vectors, variance_threshold=pca_variance)

    exemplars = []
    for row in prompt_labels.itertuples(index=False):
        prompt_id = str(row.prompt_id)
        vec = raw_vectors[prompt_id]
        if pca_transform is not None:
            vec = pca_transform.transform(vec)
        exemplars.append(
            RiskExemplar(
                prompt_id=prompt_id,
                feature=vec.astype(float).tolist(),
                expected_min_model=str(row.expected_min_model),
            )
        )
    return SufficiencyRiskModel(
        exemplars=exemplars, bandwidth=bandwidth, pca_transform=pca_transform
    )


def _risk_vector(evidence_vector: np.ndarray, prompt: str) -> np.ndarray:
    text_vector = hashed_char_ngrams(prompt, n_features=TEXT_FEATURES)
    return np.concatenate([evidence_vector.astype(np.float64), text_vector.astype(np.float64)])
