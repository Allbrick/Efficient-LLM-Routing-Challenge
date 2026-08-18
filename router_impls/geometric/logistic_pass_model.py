from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from router_impls.geometric.features import MODEL_ORDER


@dataclass
class LogisticModelCoefficients:
    model_id: str
    coefficients: list[float]
    intercept: float
    n_positive: int
    n_negative: int

    def predict_probability(self, x: np.ndarray) -> float:
        w = np.array(self.coefficients, dtype=np.float64)
        z = float(np.dot(w, x) + self.intercept)
        z = max(min(z, 500.0), -500.0)
        return 1.0 / (1.0 + math.exp(-z))

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "coefficients": self.coefficients,
            "intercept": self.intercept,
            "n_positive": self.n_positive,
            "n_negative": self.n_negative,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> LogisticModelCoefficients:
        return cls(
            model_id=str(payload["model_id"]),
            coefficients=[float(v) for v in payload["coefficients"]],
            intercept=float(payload["intercept"]),
            n_positive=int(payload.get("n_positive", 0)),
            n_negative=int(payload.get("n_negative", 0)),
        )


@dataclass
class LogisticPassModel:
    models: dict[str, LogisticModelCoefficients]

    def predict_one(self, x: np.ndarray, model_id: str) -> float:
        if model_id not in self.models:
            return 0.0
        return self.models[model_id].predict_probability(x)

    def predict_all(self, x: np.ndarray) -> dict[str, float]:
        return {model_id: self.predict_one(x, model_id) for model_id in MODEL_ORDER}

    def to_dict(self) -> dict:
        return {
            "models": {
                model_id: coeffs.to_dict()
                for model_id, coeffs in self.models.items()
            }
        }

    @classmethod
    def from_dict(cls, payload: dict) -> LogisticPassModel:
        models = {}
        for model_id, coeffs_dict in payload.get("models", {}).items():
            models[model_id] = LogisticModelCoefficients.from_dict(coeffs_dict)
        return cls(models=models)


def fit_logistic_pass_model(
    prompt_features: dict[str, np.ndarray],
    labels,
    C: float = 1.0,
    max_iter: int = 1000,
) -> LogisticPassModel:
    from sklearn.linear_model import LogisticRegression

    model_data: dict[str, tuple[list[np.ndarray], list[int]]] = {
        mid: ([], []) for mid in MODEL_ORDER
    }
    for row in labels.itertuples(index=False):
        pid = str(row.prompt_id)
        mid = str(row.model_id)
        if mid not in model_data or pid not in prompt_features:
            continue
        features_list, labels_list = model_data[mid]
        features_list.append(prompt_features[pid])
        labels_list.append(1 if bool(row.success) else 0)

    models: dict[str, LogisticModelCoefficients] = {}
    for model_id in MODEL_ORDER:
        features_list, labels_list = model_data[model_id]
        if not features_list:
            dim = next(iter(prompt_features.values())).shape[0] if prompt_features else 1
            models[model_id] = LogisticModelCoefficients(
                model_id=model_id,
                coefficients=[0.0] * dim,
                intercept=0.0,
                n_positive=0,
                n_negative=0,
            )
            continue

        X = np.array(features_list, dtype=np.float64)
        y = np.array(labels_list, dtype=np.int32)
        n_positive = int(y.sum())
        n_negative = int(len(y) - n_positive)

        unique_classes = np.unique(y)
        if len(unique_classes) < 2:
            intercept = 10.0 if unique_classes[0] == 1 else -10.0
            models[model_id] = LogisticModelCoefficients(
                model_id=model_id,
                coefficients=[0.0] * X.shape[1],
                intercept=intercept,
                n_positive=n_positive,
                n_negative=n_negative,
            )
            continue

        clf = LogisticRegression(C=C, max_iter=max_iter, solver="lbfgs")
        clf.fit(X, y)
        models[model_id] = LogisticModelCoefficients(
            model_id=model_id,
            coefficients=clf.coef_[0].tolist(),
            intercept=float(clf.intercept_[0]),
            n_positive=n_positive,
            n_negative=n_negative,
        )

    return LogisticPassModel(models=models)
