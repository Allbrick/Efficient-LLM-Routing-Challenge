from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd


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


@dataclass
class TaskClassifier:
    n_features: int
    label_centroids: dict[str, list[float]]
    exemplars: list[dict]
    difficulty_by_label: dict[str, str]
    risk_by_label: dict[str, str]
    task_type_by_label: dict[str, str]

    @classmethod
    def fit(cls, specs_df: pd.DataFrame, n_features: int = 512) -> "TaskClassifier":
        centroids = {}
        exemplars = []
        difficulty_by_label = {}
        risk_by_label = {}
        task_type_by_label = {}

        for label, group in specs_df.groupby("evaluation_type", sort=False):
            vectors = np.array([hashed_char_ngrams(prompt, n_features) for prompt in group["prompt"]])
            centroids[label] = vectors.mean(axis=0).tolist()
            difficulty_by_label[label] = _mode_or_default(group["difficulty"], "unknown")
            risk_by_label[label] = _mode_or_default(group["risk_level"], "unknown")
            task_type_by_label[label] = _mode_or_default(group["task_type"], str(label))
            for row, vector in zip(group.itertuples(index=False), vectors):
                exemplars.append(
                    {
                        "evaluation_type": label,
                        "task_type": str(row.task_type),
                        "difficulty": str(row.difficulty),
                        "risk_level": str(row.risk_level),
                        "vector": vector.tolist(),
                    }
                )

        return cls(
            n_features=n_features,
            label_centroids=centroids,
            exemplars=exemplars,
            difficulty_by_label=difficulty_by_label,
            risk_by_label=risk_by_label,
            task_type_by_label=task_type_by_label,
        )

    def predict(self, prompt: str) -> dict[str, str | float]:
        vec = hashed_char_ngrams(prompt, self.n_features)
        best_label = "unknown"
        best_score = -math.inf
        best_exemplar = None
        for exemplar in self.exemplars:
            score = float(vec @ np.array(exemplar["vector"], dtype=np.float64))
            if score > best_score:
                best_score = score
                best_label = str(exemplar["evaluation_type"])
                best_exemplar = exemplar

        if best_exemplar is not None:
            return {
                "evaluation_type": best_label,
                "task_type": str(best_exemplar["task_type"]),
                "difficulty": str(best_exemplar["difficulty"]),
                "risk_level": str(best_exemplar["risk_level"]),
                "confidence": max(best_score, 0.0),
            }

        for label, centroid in self.label_centroids.items():
            centroid_vec = np.array(centroid, dtype=np.float64)
            score = float(vec @ centroid_vec)
            if score > best_score:
                best_label = label
                best_score = score

        return {
            "evaluation_type": best_label,
            "task_type": self.task_type_by_label.get(best_label, best_label),
            "difficulty": self.difficulty_by_label.get(best_label, "unknown"),
            "risk_level": self.risk_by_label.get(best_label, "unknown"),
            "confidence": max(best_score, 0.0),
        }

    def to_dict(self) -> dict:
        return {
            "n_features": self.n_features,
            "label_centroids": self.label_centroids,
            "exemplars": self.exemplars,
            "difficulty_by_label": self.difficulty_by_label,
            "risk_by_label": self.risk_by_label,
            "task_type_by_label": self.task_type_by_label,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "TaskClassifier":
        return cls(
            n_features=int(payload["n_features"]),
            label_centroids=payload["label_centroids"],
            exemplars=payload.get("exemplars", []),
            difficulty_by_label=payload["difficulty_by_label"],
            risk_by_label=payload["risk_by_label"],
            task_type_by_label=payload["task_type_by_label"],
        )


def _mode_or_default(series: pd.Series, default: str) -> str:
    cleaned = series.dropna().astype(str)
    if cleaned.empty:
        return default
    return str(cleaned.mode().iloc[0])
