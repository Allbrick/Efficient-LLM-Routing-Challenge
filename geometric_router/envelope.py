from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Envelope:
    model_id: str
    mean: list[float]
    covariance: list[list[float]]
    inverse_covariance: list[list[float]]
    radius: float
    sample_count: int

    def distance(self, x: np.ndarray) -> float:
        diff = x - np.array(self.mean, dtype=np.float64)
        inv = np.array(self.inverse_covariance, dtype=np.float64)
        value = float(diff.T @ inv @ diff)
        return float(np.sqrt(max(value, 0.0)))

    def contains(self, x: np.ndarray, radius_multiplier: float = 1.0) -> bool:
        return self.distance(x) <= self.radius * radius_multiplier


def fit_envelope(
    model_id: str,
    features: np.ndarray,
    quantile: float = 0.90,
    epsilon: float = 1e-3,
) -> Envelope:
    if features.ndim != 2:
        raise ValueError("features must be a 2D array")
    if len(features) == 0:
        raise ValueError(f"cannot fit envelope for {model_id}: no successful samples")

    mean = features.mean(axis=0)
    if len(features) == 1:
        covariance = np.eye(features.shape[1], dtype=np.float64)
    else:
        covariance = np.cov(features, rowvar=False)
    covariance = np.atleast_2d(covariance).astype(np.float64)
    covariance = covariance + epsilon * np.eye(covariance.shape[0], dtype=np.float64)
    inverse = np.linalg.pinv(covariance)

    distances = []
    for row in features:
        diff = row - mean
        distances.append(float(np.sqrt(max(float(diff.T @ inverse @ diff), 0.0))))
    radius = float(np.quantile(distances, quantile)) if distances else 1.0
    radius = max(radius, 0.25)

    return Envelope(
        model_id=model_id,
        mean=mean.tolist(),
        covariance=covariance.tolist(),
        inverse_covariance=inverse.tolist(),
        radius=radius,
        sample_count=int(len(features)),
    )
