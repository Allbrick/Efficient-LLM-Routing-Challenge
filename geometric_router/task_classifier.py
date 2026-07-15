from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


PREDICTION_FIELDS = ("evaluation_type", "task_type", "difficulty", "risk_level")


def _hash_ngram(value: str, n_features: int) -> int:
    digest = hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "little") % n_features


def instruction_view(text: str, max_chars: int = 240) -> str:
    value = str(text)
    if "\n\n" in value:
        value = value.split("\n\n", 1)[0]
    return value[:max_chars]


def hashed_char_ngrams(text: str, n_features: int = 512, min_n: int = 2, max_n: int = 5) -> np.ndarray:
    normalized = re.sub(r"\s+", " ", instruction_view(text).lower()).strip()
    vec = np.zeros(n_features, dtype=np.float64)
    if not normalized:
        return vec
    for n in range(min_n, max_n + 1):
        if len(normalized) < n:
            continue
        for idx in range(0, len(normalized) - n + 1):
            vec[_hash_ngram(normalized[idx : idx + n], n_features)] += 1.0
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


def hashed_mixed_ngrams(text: str, n_features: int = 1024) -> np.ndarray:
    """Feature vector for task classification.

    This remains local and deterministic. It combines char n-grams, token
    unigrams, and token bigrams so labels are not decided by one nearest sample.
    """

    normalized = re.sub(r"\s+", " ", instruction_view(text).lower()).strip()
    vec = np.zeros(n_features, dtype=np.float64)
    if not normalized:
        return vec

    for n in range(2, 6):
        if len(normalized) < n:
            continue
        for idx in range(0, len(normalized) - n + 1):
            vec[_hash_ngram(f"c:{normalized[idx : idx + n]}", n_features)] += 1.0

    tokens = [token for token in re.split(r"[^0-9a-zA-Z가-힣_%+.-]+", normalized) if token]
    for token in tokens:
        vec[_hash_ngram(f"w:{token}", n_features)] += 2.0
    for left, right in zip(tokens, tokens[1:]):
        vec[_hash_ngram(f"b:{left} {right}", n_features)] += 2.5

    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


@dataclass
class LabelHead:
    field: str
    centroids: dict[str, list[float]]
    counts: dict[str, int]
    default_label: str

    @classmethod
    def fit(cls, field: str, specs_df: pd.DataFrame, vectors: np.ndarray, default_label: str) -> "LabelHead":
        centroids: dict[str, list[float]] = {}
        counts: dict[str, int] = {}
        labels = specs_df[field].fillna(default_label).astype(str).tolist()
        for label in dict.fromkeys(labels):
            indices = [idx for idx, value in enumerate(labels) if value == label]
            label_vectors = vectors[indices]
            centroid = label_vectors.mean(axis=0)
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm
            centroids[label] = centroid.astype(float).tolist()
            counts[label] = len(indices)
        return cls(field=field, centroids=centroids, counts=counts, default_label=default_label)

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "centroids": self.centroids,
            "counts": self.counts,
            "default_label": self.default_label,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "LabelHead":
        return cls(
            field=str(payload["field"]),
            centroids={str(key): [float(v) for v in value] for key, value in payload["centroids"].items()},
            counts={str(key): int(value) for key, value in payload["counts"].items()},
            default_label=str(payload.get("default_label", "unknown")),
        )


@dataclass
class TaskClassifier:
    n_features: int
    exemplars: list[dict]
    heads: dict[str, LabelHead]
    k_neighbors: int = 5
    centroid_weight: float = 0.55
    knn_weight: float = 0.40
    prior_weight: float = 0.05

    @classmethod
    def fit(cls, specs_df: pd.DataFrame, n_features: int = 1024, k_neighbors: int = 5) -> "TaskClassifier":
        clean_df = specs_df.copy()
        for field in PREDICTION_FIELDS:
            if field not in clean_df.columns:
                clean_df[field] = "unknown"
            clean_df[field] = clean_df[field].fillna("unknown").astype(str)

        vectors = np.array([hashed_mixed_ngrams(prompt, n_features) for prompt in clean_df["prompt"]])
        exemplars = []
        for row, vector in zip(clean_df.itertuples(index=False), vectors):
            exemplars.append(
                {
                    "prompt_id": str(getattr(row, "prompt_id", "")),
                    "evaluation_type": str(row.evaluation_type),
                    "task_type": str(row.task_type),
                    "difficulty": str(row.difficulty),
                    "risk_level": str(row.risk_level),
                    "vector": vector.astype(float).tolist(),
                }
            )

        heads = {
            field: LabelHead.fit(field, clean_df, vectors, default_label="unknown")
            for field in PREDICTION_FIELDS
        }
        return cls(n_features=n_features, exemplars=exemplars, heads=heads, k_neighbors=k_neighbors)

    def predict(self, prompt: str) -> dict[str, str | float | dict]:
        vec = hashed_mixed_ngrams(prompt, self.n_features)
        neighbor_scores = self._neighbor_scores(vec)
        predictions = {
            field: self._predict_field(field, vec, neighbor_scores)
            for field in PREDICTION_FIELDS
        }
        eval_prediction = predictions["evaluation_type"]
        return {
            "evaluation_type": str(eval_prediction["label"]),
            "task_type": str(predictions["task_type"]["label"]),
            "difficulty": str(predictions["difficulty"]["label"]),
            "risk_level": str(predictions["risk_level"]["label"]),
            "confidence": float(eval_prediction["confidence"]),
            "field_confidence": {
                field: float(prediction["confidence"])
                for field, prediction in predictions.items()
            },
        }

    def _neighbor_scores(self, vec: np.ndarray) -> list[tuple[float, dict]]:
        scored = []
        for exemplar in self.exemplars:
            score = float(vec @ np.array(exemplar["vector"], dtype=np.float64))
            scored.append((max(score, 0.0), exemplar))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[: max(1, self.k_neighbors)]

    def _predict_field(self, field: str, vec: np.ndarray, neighbors: list[tuple[float, dict]]) -> dict[str, Any]:
        head = self.heads[field]
        labels = list(head.centroids)
        total_count = sum(head.counts.values()) or 1
        scores: dict[str, float] = {}

        for label in labels:
            centroid = np.array(head.centroids[label], dtype=np.float64)
            centroid_score = max(float(vec @ centroid), 0.0)
            knn_score = self._knn_vote(field, label, neighbors)
            prior_score = math.log1p(head.counts[label]) / math.log1p(total_count)
            scores[label] = (
                self.centroid_weight * centroid_score
                + self.knn_weight * knn_score
                + self.prior_weight * prior_score
            )

        ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        if not ordered:
            return {"label": head.default_label, "confidence": 0.0, "margin": 0.0}
        best_label, best_score = ordered[0]
        second_score = ordered[1][1] if len(ordered) > 1 else 0.0
        confidence = best_score / max(sum(scores.values()), 1e-12)
        return {
            "label": best_label,
            "confidence": confidence,
            "margin": best_score - second_score,
        }

    def _knn_vote(self, field: str, label: str, neighbors: list[tuple[float, dict]]) -> float:
        total = sum(score for score, _ in neighbors)
        if total <= 1e-12:
            return 0.0
        label_weight = sum(score for score, exemplar in neighbors if str(exemplar[field]) == label)
        return label_weight / total

    def to_dict(self) -> dict:
        return {
            "version": 2,
            "n_features": self.n_features,
            "exemplars": self.exemplars,
            "heads": {field: head.to_dict() for field, head in self.heads.items()},
            "k_neighbors": self.k_neighbors,
            "centroid_weight": self.centroid_weight,
            "knn_weight": self.knn_weight,
            "prior_weight": self.prior_weight,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "TaskClassifier":
        if "heads" not in payload:
            return cls._from_legacy_dict(payload)
        return cls(
            n_features=int(payload["n_features"]),
            exemplars=payload.get("exemplars", []),
            heads={field: LabelHead.from_dict(data) for field, data in payload["heads"].items()},
            k_neighbors=int(payload.get("k_neighbors", 5)),
            centroid_weight=float(payload.get("centroid_weight", 0.55)),
            knn_weight=float(payload.get("knn_weight", 0.40)),
            prior_weight=float(payload.get("prior_weight", 0.05)),
        )

    @classmethod
    def _from_legacy_dict(cls, payload: dict) -> "TaskClassifier":
        exemplars = payload.get("exemplars", [])
        specs = pd.DataFrame(
            [
                {
                    "prompt_id": str(idx),
                    "prompt": "",
                    "evaluation_type": item.get("evaluation_type", "unknown"),
                    "task_type": item.get("task_type", "unknown"),
                    "difficulty": item.get("difficulty", "unknown"),
                    "risk_level": item.get("risk_level", "unknown"),
                }
                for idx, item in enumerate(exemplars)
            ]
        )
        if specs.empty:
            specs = pd.DataFrame(
                [
                    {
                        "prompt_id": "legacy-empty",
                        "prompt": "",
                        "evaluation_type": "unknown",
                        "task_type": "unknown",
                        "difficulty": "unknown",
                        "risk_level": "unknown",
                    }
                ]
            )
        classifier = cls.fit(specs, n_features=int(payload.get("n_features", 1024)))
        classifier.exemplars = exemplars
        return classifier
