from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

from routing_stack.input import analyze_text_prompt


LABELS = ("cheap", "mid", "premium")


@dataclass
class PromptLabelPrediction:
    selected_label: str
    probabilities: dict[str, float]
    raw_probabilities: dict[str, float]
    geometry: dict[str, Any]


class PromptLabelRouterModel:
    """Prompt/정답 CSV로 학습하는 로컬 라우팅 classifier입니다."""

    def __init__(self) -> None:
        self.word_vectorizer = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=1)
        self.char_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=1)
        self.scaler = StandardScaler()
        self.classifier = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
        self.labels = LABELS
        self.class_centroids: dict[str, csr_matrix] = {}
        self.training_features = None
        self.training_prompts: list[str] = []
        self.training_labels: list[str] = []

    def fit(self, prompts: list[str], labels: list[str]) -> "PromptLabelRouterModel":
        normalized_labels = [_normalize_label(label) for label in labels]
        if len(set(normalized_labels)) < 2:
            raise ValueError("학습에는 최소 2개 이상의 label class가 필요합니다.")
        word = self.word_vectorizer.fit_transform(prompts)
        char = self.char_vectorizer.fit_transform(prompts)
        manual = self.scaler.fit_transform(_manual_features(prompts))
        features = hstack([word, char, csr_matrix(manual)])
        self.classifier.fit(features, normalized_labels)
        self.labels = tuple(str(label) for label in self.classifier.classes_)
        self._fit_geometry(features.tocsr(), prompts, normalized_labels)
        return self

    def predict(self, prompt: str) -> PromptLabelPrediction:
        features = self._transform([prompt])
        probabilities_raw = self.classifier.predict_proba(features)[0]
        raw_probabilities = {
            str(label): round(float(probability), 6)
            for label, probability in zip(self.classifier.classes_, probabilities_raw, strict=True)
        }
        for label in LABELS:
            raw_probabilities.setdefault(label, 0.0)
        geometry = self._geometry(features)
        probabilities = _blend_probabilities(raw_probabilities, geometry.get("centroid_probabilities", {}))
        probabilities = _apply_exact_neighbor(probabilities, geometry.get("nearest_examples", []))
        selected = max(LABELS, key=lambda label: (probabilities.get(label, 0.0), -_label_rank(label)))
        return PromptLabelPrediction(
            selected_label=selected,
            probabilities=probabilities,
            raw_probabilities=raw_probabilities,
            geometry=geometry,
        )

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: str | Path) -> "PromptLabelRouterModel":
        model = joblib.load(path)
        if not isinstance(model, cls):
            raise TypeError("artifact가 PromptLabelRouterModel 형식이 아닙니다.")
        model._ensure_geometry_attrs()
        return model

    def _transform(self, prompts: list[str]):
        word = self.word_vectorizer.transform(prompts)
        char = self.char_vectorizer.transform(prompts)
        manual = self.scaler.transform(_manual_features(prompts))
        return hstack([word, char, csr_matrix(manual)])

    def _fit_geometry(self, features: csr_matrix, prompts: list[str], labels: list[str]) -> None:
        self.training_features = features
        self.training_prompts = list(prompts)
        self.training_labels = list(labels)
        self.class_centroids = {}
        labels_array = np.asarray(labels)
        for label in LABELS:
            mask = labels_array == label
            if np.any(mask):
                self.class_centroids[label] = csr_matrix(features[mask].mean(axis=0))

    def _geometry(self, features) -> dict[str, Any]:
        self._ensure_geometry_attrs()
        centroid_distances = _centroid_distances(features, self.class_centroids)
        centroid_probabilities = _centroid_probabilities(centroid_distances)
        nearest_examples = _nearest_examples(
            features,
            self.training_features,
            self.training_prompts,
            self.training_labels,
            limit=3,
        )
        sorted_distances = sorted(centroid_distances.items(), key=lambda item: item[1])
        nearest_label = sorted_distances[0][0] if sorted_distances else None
        margin = None
        if len(sorted_distances) >= 2:
            margin = round(float(sorted_distances[1][1] - sorted_distances[0][1]), 6)
        return {
            "centroid_distances": centroid_distances,
            "centroid_probabilities": centroid_probabilities,
            "nearest_centroid_label": nearest_label,
            "centroid_margin": margin,
            "nearest_examples": nearest_examples,
        }

    def _ensure_geometry_attrs(self) -> None:
        if not hasattr(self, "class_centroids"):
            self.class_centroids = {}
        if not hasattr(self, "training_features"):
            self.training_features = None
        if not hasattr(self, "training_prompts"):
            self.training_prompts = []
        if not hasattr(self, "training_labels"):
            self.training_labels = []


def _manual_features(prompts: list[str]) -> np.ndarray:
    rows: list[list[float]] = []
    for prompt in prompts:
        features = analyze_text_prompt(prompt).to_dict()
        rows.append(
            [
                float(features.get("prompt_length", 0)),
                float(features.get("whitespace_token_count", 0)),
                float(features.get("estimated_input_tokens", 0)),
                float(features.get("estimated_output_tokens", 0)),
                float(features.get("code_token_pressure", 0.0)),
                float(features.get("json_or_table_pressure", 0.0)),
                float(features.get("line_count", 0)),
                float(features.get("punctuation_ratio", 0.0)),
                float(features.get("digit_ratio", 0.0)),
                float(bool(features.get("code_like", False))),
                float(bool(features.get("simple_directive", False))),
                float(bool(features.get("simple_conversion", False))),
                float(bool(features.get("technical_explanation", False))),
                float(bool(features.get("comparison_task", False))),
                float(bool(features.get("design_task", False))),
                float(bool(features.get("advanced_reasoning_task", False))),
                float(features.get("task_complexity_hint", 0.0)),
            ]
        )
    return np.asarray(rows, dtype=np.float64)


def _normalize_label(label: Any) -> str:
    normalized = str(label or "").strip().lower()
    if normalized not in LABELS:
        raise ValueError(f"지원하지 않는 label입니다: {label}")
    return normalized


def _label_rank(label: str) -> int:
    return {"cheap": 0, "mid": 1, "premium": 2}.get(label, 99)


def _centroid_distances(features, centroids: dict[str, csr_matrix]) -> dict[str, float]:
    distances = {}
    for label, centroid in centroids.items():
        similarity = float(cosine_similarity(features, centroid)[0][0])
        distances[label] = round(float(1.0 - similarity), 6)
    return distances


def _centroid_probabilities(distances: dict[str, float]) -> dict[str, float]:
    if not distances:
        return {}
    labels = list(distances)
    scores = np.asarray([-distances[label] for label in labels], dtype=np.float64)
    scores = scores - scores.max()
    exp_scores = np.exp(scores)
    total = float(exp_scores.sum())
    if total <= 0:
        return {}
    return {label: round(float(score / total), 6) for label, score in zip(labels, exp_scores, strict=True)}


def _blend_probabilities(raw: dict[str, float], geometric: dict[str, float]) -> dict[str, float]:
    if not geometric:
        return {label: round(float(raw.get(label, 0.0)), 6) for label in LABELS}
    blended = {}
    for label in LABELS:
        blended[label] = (0.75 * float(raw.get(label, 0.0))) + (0.25 * float(geometric.get(label, 0.0)))
    total = sum(blended.values()) or 1.0
    return {label: round(float(value / total), 6) for label, value in blended.items()}


def _apply_exact_neighbor(probabilities: dict[str, float], nearest_examples: list[dict[str, Any]]) -> dict[str, float]:
    if not nearest_examples:
        return probabilities
    nearest = nearest_examples[0]
    label = str(nearest.get("label", ""))
    similarity = float(nearest.get("similarity", 0.0))
    if label not in LABELS or similarity < 0.999999:
        return probabilities
    return {candidate: (0.98 if candidate == label else 0.01) for candidate in LABELS}


def _nearest_examples(features, training_features, prompts: list[str], labels: list[str], limit: int) -> list[dict[str, Any]]:
    if training_features is None or not prompts:
        return []
    similarities = cosine_similarity(features, training_features)[0]
    top_indices = np.argsort(similarities)[::-1][:limit]
    examples = []
    for index in top_indices:
        examples.append(
            {
                "prompt": prompts[int(index)],
                "label": labels[int(index)],
                "similarity": round(float(similarities[int(index)]), 6),
            }
        )
    return examples
