from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from routing_stack.input import analyze_text_prompt


LABELS = ("cheap", "mid", "premium")


@dataclass
class PromptLabelPrediction:
    selected_label: str
    probabilities: dict[str, float]


class PromptLabelRouterModel:
    """Prompt/정답 CSV로 학습하는 로컬 라우팅 classifier입니다."""

    def __init__(self) -> None:
        self.word_vectorizer = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=1)
        self.char_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=1)
        self.scaler = StandardScaler()
        self.classifier = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
        self.labels = LABELS

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
        return self

    def predict(self, prompt: str) -> PromptLabelPrediction:
        features = self._transform([prompt])
        probabilities_raw = self.classifier.predict_proba(features)[0]
        probabilities = {
            str(label): round(float(probability), 6)
            for label, probability in zip(self.classifier.classes_, probabilities_raw, strict=True)
        }
        for label in LABELS:
            probabilities.setdefault(label, 0.0)
        selected = max(LABELS, key=lambda label: (probabilities.get(label, 0.0), -_label_rank(label)))
        return PromptLabelPrediction(selected_label=selected, probabilities=probabilities)

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: str | Path) -> "PromptLabelRouterModel":
        model = joblib.load(path)
        if not isinstance(model, cls):
            raise TypeError("artifact가 PromptLabelRouterModel 형식이 아닙니다.")
        return model

    def _transform(self, prompts: list[str]):
        word = self.word_vectorizer.transform(prompts)
        char = self.char_vectorizer.transform(prompts)
        manual = self.scaler.transform(_manual_features(prompts))
        return hstack([word, char, csr_matrix(manual)])


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
