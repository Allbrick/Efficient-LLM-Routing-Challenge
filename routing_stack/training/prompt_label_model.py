from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

from routing_stack.input import analyze_text_prompt
from routing_stack.training.prompt_label_csv import score_to_model_slot


MODEL_SLOTS = ("cheap", "mid", "premium")
LABELS = MODEL_SLOTS
BUCKET_MIDPOINTS = {"cheap": 20.0, "mid": 55.0, "premium": 85.0}


@dataclass
class PromptLabelPrediction:
    routing_score: float
    raw_routing_score: float
    selected_model_id: str
    bucket_scores: dict[str, float]
    raw_bucket_scores: dict[str, float]
    geometry: dict[str, Any]

    @property
    def selected_label(self) -> str:
        return self.selected_model_id

    @property
    def probabilities(self) -> dict[str, float]:
        return self.bucket_scores

    @property
    def raw_probabilities(self) -> dict[str, float]:
        return self.raw_bucket_scores


class PromptLabelRouterModel:
    """Prompt/routing_score regressor used by the learned_label router."""

    def __init__(self) -> None:
        self.word_vectorizer = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=1)
        self.char_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=1)
        self.scaler = StandardScaler()
        self.regressor = Ridge(alpha=1.0)
        self.labels = MODEL_SLOTS
        self.class_centroids: dict[str, csr_matrix] = {}
        self.training_features = None
        self.training_prompts: list[str] = []
        self.training_scores: list[float] = []
        self.training_labels: list[str] = []

    def fit(self, prompts: list[str], routing_scores: list[float]) -> "PromptLabelRouterModel":
        scores = np.asarray([_normalize_score(score) for score in routing_scores], dtype=np.float64)
        if len(prompts) != len(scores):
            raise ValueError("prompts and routing_scores must have the same length.")
        if len(scores) < 2:
            raise ValueError("At least two training rows are required.")

        word = self.word_vectorizer.fit_transform(prompts)
        char = self.char_vectorizer.fit_transform(prompts)
        manual = self.scaler.fit_transform(_manual_features(prompts))
        features = hstack([word, char, csr_matrix(manual)]).tocsr()
        self.regressor.fit(features, scores)
        self._fit_geometry(features, prompts, scores.tolist())
        return self

    def predict(self, prompt: str) -> PromptLabelPrediction:
        features = self._transform([prompt])
        raw_score = _clip_score(float(self.regressor.predict(features)[0]))
        geometry = self._geometry(features)
        centroid_score = geometry.get("centroid_routing_score")
        nearest_score = geometry.get("nearest_routing_score")
        if nearest_score is not None:
            centroid_component = float(centroid_score) if centroid_score is not None else raw_score
            blended_score = (0.30 * raw_score) + (0.10 * centroid_component) + (0.60 * float(nearest_score))
        elif centroid_score is None:
            blended_score = raw_score
        else:
            blended_score = (0.75 * raw_score) + (0.25 * float(centroid_score))
        blended_score = _apply_exact_neighbor_score(blended_score, geometry.get("nearest_examples", []))
        routing_score = round(_clip_score(blended_score), 3)
        selected = score_to_model_slot(routing_score)
        return PromptLabelPrediction(
            routing_score=routing_score,
            raw_routing_score=round(raw_score, 3),
            selected_model_id=selected,
            bucket_scores=_bucket_scores(routing_score),
            raw_bucket_scores=_bucket_scores(raw_score),
            geometry=geometry,
        )

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: str | Path) -> "PromptLabelRouterModel":
        model = joblib.load(path)
        if not isinstance(model, cls):
            raise TypeError("artifact is not a PromptLabelRouterModel.")
        model._ensure_geometry_attrs()
        return model

    def _transform(self, prompts: list[str]):
        word = self.word_vectorizer.transform(prompts)
        char = self.char_vectorizer.transform(prompts)
        manual = self.scaler.transform(_manual_features(prompts))
        return hstack([word, char, csr_matrix(manual)]).tocsr()

    def _fit_geometry(self, features: csr_matrix, prompts: list[str], scores: list[float]) -> None:
        self.training_features = features
        self.training_prompts = list(prompts)
        self.training_scores = [float(score) for score in scores]
        self.training_labels = [score_to_model_slot(score) for score in scores]
        self.class_centroids = {}
        labels_array = np.asarray(self.training_labels)
        for label in MODEL_SLOTS:
            mask = labels_array == label
            if np.any(mask):
                self.class_centroids[label] = csr_matrix(features[mask].mean(axis=0))

    def _geometry(self, features) -> dict[str, Any]:
        self._ensure_geometry_attrs()
        centroid_distances = _centroid_distances(features, self.class_centroids)
        centroid_probabilities = _centroid_probabilities(centroid_distances)
        centroid_score = _weighted_bucket_score(centroid_probabilities)
        nearest_examples = _nearest_examples(
            features,
            self.training_features,
            self.training_prompts,
            self.training_scores,
            self.training_labels,
            limit=3,
        )
        nearest_score = _nearest_score(nearest_examples)
        sorted_distances = sorted(centroid_distances.items(), key=lambda item: item[1])
        nearest_label = sorted_distances[0][0] if sorted_distances else None
        margin = None
        if len(sorted_distances) >= 2:
            margin = round(float(sorted_distances[1][1] - sorted_distances[0][1]), 6)
        return {
            "centroid_distances": centroid_distances,
            "centroid_probabilities": centroid_probabilities,
            "centroid_routing_score": centroid_score,
            "nearest_routing_score": nearest_score,
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
        if not hasattr(self, "training_scores"):
            self.training_scores = []
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


def _normalize_score(score: Any) -> float:
    try:
        parsed = float(score)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid routing_score: {score}") from exc
    if not 0.0 <= parsed <= 100.0:
        raise ValueError(f"routing_score must be between 0 and 100: {score}")
    return parsed


def _clip_score(score: float) -> float:
    return max(0.0, min(100.0, score))


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


def _weighted_bucket_score(bucket_weights: dict[str, float]) -> float | None:
    if not bucket_weights:
        return None
    total = sum(float(value) for value in bucket_weights.values())
    if total <= 0:
        return None
    score = sum(float(bucket_weights.get(label, 0.0)) * BUCKET_MIDPOINTS[label] for label in MODEL_SLOTS) / total
    return round(_clip_score(score), 3)


def _bucket_scores(score: float) -> dict[str, float]:
    labels = list(MODEL_SLOTS)
    logits = np.asarray([-abs(float(score) - BUCKET_MIDPOINTS[label]) / 12.0 for label in labels], dtype=np.float64)
    logits = logits - logits.max()
    exp_scores = np.exp(logits)
    total = float(exp_scores.sum()) or 1.0
    return {label: round(float(value / total), 6) for label, value in zip(labels, exp_scores, strict=True)}


def _apply_exact_neighbor_score(score: float, nearest_examples: list[dict[str, Any]]) -> float:
    if not nearest_examples:
        return score
    nearest = nearest_examples[0]
    if float(nearest.get("similarity", 0.0)) < 0.999999:
        return score
    return _clip_score(float(nearest.get("routing_score", score)))


def _nearest_score(nearest_examples: list[dict[str, Any]]) -> float | None:
    close_examples = [example for example in nearest_examples if float(example.get("similarity", 0.0)) >= 0.65]
    if not close_examples:
        return None
    weights = np.asarray([float(example.get("similarity", 0.0)) for example in close_examples], dtype=np.float64)
    scores = np.asarray([float(example.get("routing_score", 0.0)) for example in close_examples], dtype=np.float64)
    total = float(weights.sum())
    if total <= 0:
        return None
    return round(_clip_score(float(np.dot(weights, scores) / total)), 3)


def _nearest_examples(
    features,
    training_features,
    prompts: list[str],
    scores: list[float],
    labels: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    if training_features is None or not prompts:
        return []
    similarities = cosine_similarity(features, training_features)[0]
    top_indices = np.argsort(similarities)[::-1][:limit]
    examples = []
    for index in top_indices:
        int_index = int(index)
        examples.append(
            {
                "prompt": prompts[int_index],
                "routing_score": round(float(scores[int_index]), 3),
                "label": labels[int_index],
                "similarity": round(float(similarities[int_index]), 6),
            }
        )
    return examples
