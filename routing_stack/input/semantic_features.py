from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np


DEFAULT_SEMANTIC_DIM = 64
SEMANTIC_LABELS = ("cheap", "mid", "premium")


class PromptEncoder(Protocol):
    name: str
    dimension: int

    def encode(self, prompts: list[str]) -> np.ndarray:
        ...


def _hash_index(value: str, dimension: int) -> int:
    digest = hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "little") % dimension


@dataclass
class HashPromptEncoder:
    dimension: int = DEFAULT_SEMANTIC_DIM
    name: str = "hash-char-token-v1"

    def encode(self, prompts: list[str]) -> np.ndarray:
        return np.array([self._encode_one(prompt) for prompt in prompts], dtype=np.float64)

    def _encode_one(self, prompt: str) -> np.ndarray:
        text = re.sub(r"\s+", " ", str(prompt).lower()).strip()
        vec = np.zeros(self.dimension, dtype=np.float64)
        if not text:
            return vec
        tokens = [token for token in re.split(r"[^0-9a-zA-Z가-힣_%+.-]+", text) if token]
        for token in tokens:
            vec[_hash_index(f"w:{token}", self.dimension)] += 2.0
        for left, right in zip(tokens, tokens[1:]):
            vec[_hash_index(f"b:{left} {right}", self.dimension)] += 2.5
        for n in range(2, 5):
            if len(text) < n:
                continue
            for idx in range(0, len(text) - n + 1):
                vec[_hash_index(f"c:{text[idx : idx + n]}", self.dimension)] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec


class SentenceTransformerPromptEncoder:
    def __init__(self, model_name: str = "intfloat/multilingual-e5-small"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for SentenceTransformerPromptEncoder. "
                "Install it only when building optional semantic features."
            ) from exc
        self.name = model_name
        self._model = SentenceTransformer(model_name)
        self.dimension = int(self._model.get_sentence_embedding_dimension())

    def encode(self, prompts: list[str]) -> np.ndarray:
        values = [f"query: {prompt}" for prompt in prompts]
        vectors = self._model.encode(values, normalize_embeddings=True)
        return np.asarray(vectors, dtype=np.float64)


@dataclass
class SemanticFeatureIndex:
    encoder_name: str
    dimension: int
    centroids: dict[str, list[float]]
    counts: dict[str, int]

    @classmethod
    def fit(cls, prompts: list[str], labels: list[str], encoder: PromptEncoder | None = None) -> "SemanticFeatureIndex":
        if len(prompts) != len(labels):
            raise ValueError("prompts and labels must have the same length")
        encoder = encoder or HashPromptEncoder()
        vectors = encoder.encode(prompts)
        centroids: dict[str, list[float]] = {}
        counts: dict[str, int] = {}
        for label in SEMANTIC_LABELS:
            indices = [idx for idx, value in enumerate(labels) if value == label]
            if not indices:
                centroid = np.zeros(encoder.dimension, dtype=np.float64)
            else:
                centroid = vectors[indices].mean(axis=0)
                norm = np.linalg.norm(centroid)
                if norm > 0:
                    centroid = centroid / norm
            centroids[label] = centroid.astype(float).tolist()
            counts[label] = len(indices)
        return cls(
            encoder_name=encoder.name,
            dimension=int(encoder.dimension),
            centroids=centroids,
            counts=counts,
        )

    def feature_vector(self, prompt: str, encoder: PromptEncoder | None = None) -> np.ndarray:
        encoder = encoder or self._default_encoder()
        if encoder.dimension != self.dimension:
            raise ValueError(f"encoder dimension {encoder.dimension} does not match semantic index dimension {self.dimension}")
        vector = encoder.encode([prompt])[0]
        similarities = []
        for label in SEMANTIC_LABELS:
            centroid = np.array(self.centroids.get(label, [0.0] * self.dimension), dtype=np.float64)
            similarities.append(max(float(vector @ centroid), 0.0))
        distances = [1.0 - value for value in similarities]
        ordered = sorted(similarities, reverse=True)
        margin = ordered[0] - ordered[1] if len(ordered) > 1 else ordered[0]
        uncertainty = 1.0 - min(max(margin, 0.0), 1.0)
        return np.array([*distances, uncertainty], dtype=np.float64)

    def explain(self, prompt: str, encoder: PromptEncoder | None = None) -> dict[str, float | str]:
        vector = self.feature_vector(prompt, encoder=encoder)
        return {
            "semantic_encoder": self.encoder_name,
            "nearest_cheap_distance": float(vector[0]),
            "nearest_mid_distance": float(vector[1]),
            "nearest_premium_distance": float(vector[2]),
            "semantic_uncertainty": float(vector[3]),
        }

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "encoder_name": self.encoder_name,
            "dimension": self.dimension,
            "centroids": self.centroids,
            "counts": self.counts,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "SemanticFeatureIndex":
        return cls(
            encoder_name=str(payload["encoder_name"]),
            dimension=int(payload["dimension"]),
            centroids={str(key): [float(value) for value in values] for key, values in payload["centroids"].items()},
            counts={str(key): int(value) for key, value in payload.get("counts", {}).items()},
        )

    def save(self, path: str | Path) -> None:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "SemanticFeatureIndex":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def _default_encoder(self) -> PromptEncoder:
        if self.encoder_name == "hash-char-token-v1":
            return HashPromptEncoder(dimension=self.dimension)
        return SentenceTransformerPromptEncoder(self.encoder_name)
