from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from routing_stack.input.token_estimator import estimate_text_tokens
from router_impls.geometric.task_classifier import hashed_char_ngrams


MODEL_ORDER = ("cheap", "mid", "premium")
ROUTE_ACTIONS = ("abstain", "cheap", "mid", "premium")
MODEL_RANK = {model: idx for idx, model in enumerate(MODEL_ORDER)}
CHAR_NGRAM_FEATURES = 16

DIFFICULTY_SCORE = {
    "trivial": 0.10,
    "easy": 0.25,
    "medium": 0.55,
    "hard": 0.85,
    "unknown": 0.65,
}

RISK_SCORE = {
    "low": 0.10,
    "medium": 0.50,
    "high": 0.90,
    "unknown": 0.60,
}

EVALUATION_TYPES = (
    "unknown",
    "exact_match",
    "numeric_check",
    "numeric_count",
    "unit_test",
    "exact_json",
    "constraint_check",
    "rubric_check",
    "required_clarification",
    "refusal_check",
    "clarification",
)

TASK_HINTS = {
    "code": ("코드", "함수", "파이썬", "javascript", "typescript", "def ", "function", "class "),
    "legal": ("계약", "법적", "법률", "조항", "무효", "관할"),
    "math": ("계산", "값", "+", "-", "*", "/", "수식", "숫자"),
    "data": ("json", "csv", "표", "배열", "필드"),
    "summary": ("요약", "불릿", "bullet", "정리"),
    "architecture": ("설계", "시스템", "파이프라인", "멀티테넌트", "분산", "장애"),
}

MISSING_CONTEXT_TERMS = ("다음", "이 ", "해당", "위 ", "아래", "첨부", "코드", "계약", "문서", "파일", "조항")
CLARIFICATION_TASK_TERMS = ("고쳐", "수정", "판단", "분석", "검토", "유효", "무효")


@dataclass(frozen=True)
class PromptEvidence:
    difficulty_score: float
    risk_score: float
    condition_count: float
    missing_context: float
    exact_answer: float
    code_like: float
    length_norm: float
    line_norm: float
    eval_type_id: float
    char_ngram_vector: tuple[float, ...]
    token_count_norm: float
    estimated_input_tokens_norm: float
    cost_estimate_norm: float

    def as_vector(self) -> np.ndarray:
        base = np.array(
            [
                self.difficulty_score,
                self.risk_score,
                self.condition_count,
                self.missing_context,
                self.exact_answer,
                self.code_like,
                self.length_norm,
                self.line_norm,
                self.eval_type_id,
            ],
            dtype=np.float64,
        )
        text_shape = np.array(self.char_ngram_vector, dtype=np.float64)
        token_cost = np.array(
            [
                self.token_count_norm,
                self.estimated_input_tokens_norm,
                self.cost_estimate_norm,
            ],
            dtype=np.float64,
        )
        return np.concatenate([base, text_shape, token_cost])


class EvidenceExtractor:
    """Extract compact coordinates from metadata and structural prompt features."""

    def transform(
        self,
        prompt: str,
        task_type: str = "",
        difficulty: str = "",
        risk_level: str = "",
        evaluation_type: str = "",
    ) -> PromptEvidence:
        text = str(prompt)
        lowered = text.lower()
        code_like = self._has_hint(lowered, TASK_HINTS["code"])
        eval_type = str(evaluation_type or "unknown")
        exact_answer = self._exact_answer(text, eval_type)
        length_norm = min(len(text) / 500.0, 1.0)
        line_norm = min((text.count("\n") + 1) / 12.0, 1.0)
        whitespace_tokens = len(text.split())
        estimated_input_tokens = estimate_text_tokens(text)

        inferred_difficulty = self._infer_difficulty(text, lowered, task_type, eval_type)
        inferred_risk = self._infer_risk(text, lowered, task_type)
        difficulty_score = DIFFICULTY_SCORE.get(str(difficulty).lower(), inferred_difficulty)
        risk_score = RISK_SCORE.get(str(risk_level).lower(), inferred_risk)

        return PromptEvidence(
            difficulty_score=float(difficulty_score),
            risk_score=float(risk_score),
            condition_count=float(self._condition_count(text, lowered)),
            missing_context=float(self._missing_context(text)),
            exact_answer=float(exact_answer),
            code_like=float(code_like),
            length_norm=float(length_norm),
            line_norm=float(line_norm),
            eval_type_id=float(self._eval_type_id(eval_type)),
            char_ngram_vector=tuple(
                float(value) for value in hashed_char_ngrams(text, n_features=CHAR_NGRAM_FEATURES)
            ),
            token_count_norm=float(min(whitespace_tokens / 120.0, 1.0)),
            estimated_input_tokens_norm=float(min(estimated_input_tokens / 800.0, 1.0)),
            cost_estimate_norm=float(min((estimated_input_tokens / 1000.0) * (1.0 + 2.0 * code_like), 1.0)),
        )

    def explain(
        self,
        prompt: str,
        task_type: str = "",
        difficulty: str = "",
        risk_level: str = "",
        evaluation_type: str = "",
    ) -> dict[str, float]:
        evidence = self.transform(prompt, task_type, difficulty, risk_level, evaluation_type)
        return {
            "difficulty_score": evidence.difficulty_score,
            "risk_score": evidence.risk_score,
            "condition_count": evidence.condition_count,
            "missing_context": evidence.missing_context,
            "exact_answer": evidence.exact_answer,
            "code_like": evidence.code_like,
            "length_norm": evidence.length_norm,
            "line_norm": evidence.line_norm,
            "eval_type_id": evidence.eval_type_id,
            "char_ngram_dim": float(len(evidence.char_ngram_vector)),
            "char_ngram_norm": float(np.linalg.norm(np.array(evidence.char_ngram_vector, dtype=np.float64))),
            "token_count_norm": evidence.token_count_norm,
            "estimated_input_tokens_norm": evidence.estimated_input_tokens_norm,
            "cost_estimate_norm": evidence.cost_estimate_norm,
        }

    def _infer_difficulty(self, text: str, lowered: str, task_type: str, evaluation_type: str) -> float:
        if evaluation_type in {"exact_match", "numeric_check", "numeric_count"}:
            return 0.10
        if self._missing_context(text):
            return 0.65
        if self._has_hint(lowered, TASK_HINTS["architecture"]):
            return 0.85
        if self._has_hint(lowered, TASK_HINTS["code"]) and self._condition_count(text, lowered) >= 0.25:
            return 0.60
        if len(text) > 220 or self._condition_count(text, lowered) >= 0.50:
            return 0.75
        if task_type:
            if "hard" in task_type or "architecture" in task_type or "distributed" in task_type:
                return 0.85
            if "medium" in task_type or "constraints" in task_type:
                return 0.55
        return 0.30

    def _infer_risk(self, text: str, lowered: str, task_type: str) -> float:
        if self._missing_context(text) and self._has_hint(lowered, TASK_HINTS["legal"]):
            return 0.90
        if self._has_hint(lowered, TASK_HINTS["legal"]):
            return 0.80
        if "medical" in task_type or "finance" in task_type:
            return 0.80
        if self._has_hint(lowered, TASK_HINTS["architecture"]):
            return 0.55
        return 0.15

    def _condition_count(self, text: str, lowered: str) -> float:
        separators = len(re.findall(r",|;| 그리고 | 또한 | 각각 | 모두 | and | or | must | should ", lowered))
        bullets = len(re.findall(r"^\s*[-*0-9]", text, flags=re.MULTILINE))
        return min(float(separators + bullets), 8.0) / 8.0

    def _missing_context(self, text: str) -> float:
        short = len(text) <= 80
        has_pointer = any(term in text for term in MISSING_CONTEXT_TERMS)
        has_task = any(term in text for term in CLARIFICATION_TASK_TERMS)
        return 1.0 if short and has_pointer and has_task else 0.0

    def _exact_answer(self, text: str, evaluation_type: str) -> float:
        if evaluation_type in {"exact_match", "numeric_check", "numeric_count"}:
            return 1.0
        has_simple_math = bool(re.search(r"\d+\s*[+\-*/]\s*\d+", text))
        return 1.0 if has_simple_math else 0.0

    def _has_hint(self, lowered: str, hints: tuple[str, ...]) -> float:
        return 1.0 if any(hint.lower() in lowered for hint in hints) else 0.0

    def _eval_type_id(self, evaluation_type: str) -> float:
        if evaluation_type not in EVALUATION_TYPES:
            evaluation_type = "unknown"
        return EVALUATION_TYPES.index(evaluation_type) / max(len(EVALUATION_TYPES) - 1, 1)

