from __future__ import annotations

import math
import re
from dataclasses import dataclass

import numpy as np

from routing_stack.input.token_estimator import estimate_prompt_tokens
from routing_stack.input.text_features import analyze_text_prompt
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
    # Advanced reasoning demands premium regardless of prompt length. Without
    # this group a short proof request ("P != NP임을 증명해줘.") falls through to
    # the length rules and is scored as an easy prompt.
    "reasoning": (
        "증명",
        "반례",
        "귀류",
        "복잡도",
        "점근",
        "최적해",
        "수렴",
        "np-hard",
        "np-완전",
        "np완전",
        "p=np",
        "p != np",
        "p ≠ np",
        "prove",
        "proof",
        "theorem",
        "counterexample",
        "np-complete",
        "asymptotic",
    ),
}

MISSING_CONTEXT_TERMS = ("다음", "이 ", "해당", "위 ", "아래", "첨부", "코드", "계약", "문서", "파일", "조항")
CLARIFICATION_TASK_TERMS = ("고쳐", "수정", "판단", "분석", "검토", "유효", "무효")

# Log1p normalization denominators for token/cost features
_LOG1P_120 = math.log1p(120)
_LOG1P_800 = math.log1p(800)
_LOG1P_1200 = math.log1p(1200)


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
    estimated_output_tokens_norm: float
    cost_estimate_norm: float
    code_token_pressure: float
    json_or_table_pressure: float
    # Phase 2: Interaction features
    difficulty_risk_interaction: float = 0.0
    code_complexity_interaction: float = 0.0
    cost_pressure_interaction: float = 0.0

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
                self.estimated_output_tokens_norm,
                self.cost_estimate_norm,
                self.code_token_pressure,
                self.json_or_table_pressure,
            ],
            dtype=np.float64,
        )
        interaction = np.array(
            [
                self.difficulty_risk_interaction,
                self.code_complexity_interaction,
                self.cost_pressure_interaction,
            ],
            dtype=np.float64,
        )
        return np.concatenate([base, text_shape, token_cost, interaction])


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
        text_features = analyze_text_prompt(text)
        semantic_text = text_features.compressed_prompt or text
        lowered = semantic_text.lower()
        code_like = self._has_hint(lowered, TASK_HINTS["code"])
        eval_type = str(evaluation_type or "unknown")
        exact_answer = self._exact_answer(semantic_text, eval_type)
        length_norm = min(len(semantic_text) / 500.0, 1.0)
        line_norm = min((semantic_text.count("\n") + 1) / 12.0, 1.0)
        whitespace_tokens = len(semantic_text.split())
        token_estimate = estimate_prompt_tokens(semantic_text)

        inferred_difficulty = self._infer_difficulty(semantic_text, lowered, task_type, eval_type)
        inferred_risk = self._infer_risk(semantic_text, lowered, task_type)
        difficulty_score = DIFFICULTY_SCORE.get(str(difficulty).lower(), inferred_difficulty)
        risk_score = RISK_SCORE.get(str(risk_level).lower(), inferred_risk)
        # A coarse label can undersell the prompt: the task classifier calls
        # "P != NP임을 증명해줘." medium (0.55) because it is short. When the text
        # carries an unambiguous architecture/proof signal, raise the floor so a
        # label never routes premium-grade work to cheap.
        if self._has_strong_difficulty_signal(lowered, eval_type):
            difficulty_score = max(float(difficulty_score), 0.85)

        condition_count_val = float(self._condition_count(semantic_text, lowered))

        # Log1p transform for token/cost features (Phase 2)
        token_count_norm = float(min(math.log1p(whitespace_tokens) / _LOG1P_120, 1.0))
        estimated_input_tokens_norm = float(
            min(math.log1p(token_estimate.estimated_input_tokens) / _LOG1P_800, 1.0)
        )
        estimated_output_tokens_norm = float(
            min(math.log1p(token_estimate.estimated_output_tokens) / _LOG1P_1200, 1.0)
        )
        raw_cost_estimate = (
            token_estimate.estimated_input_tokens + 0.35 * token_estimate.estimated_output_tokens
        )
        cost_estimate_norm = float(min(math.log1p(raw_cost_estimate) / _LOG1P_1200, 1.0))

        return PromptEvidence(
            difficulty_score=float(difficulty_score),
            risk_score=float(risk_score),
            condition_count=condition_count_val,
            missing_context=float(self._missing_context(semantic_text)),
            exact_answer=float(exact_answer),
            code_like=float(code_like),
            length_norm=float(length_norm),
            line_norm=float(line_norm),
            eval_type_id=float(self._eval_type_id(eval_type)),
            char_ngram_vector=tuple(
                float(value) for value in hashed_char_ngrams(semantic_text, n_features=CHAR_NGRAM_FEATURES)
            ),
            token_count_norm=token_count_norm,
            estimated_input_tokens_norm=estimated_input_tokens_norm,
            estimated_output_tokens_norm=estimated_output_tokens_norm,
            cost_estimate_norm=cost_estimate_norm,
            code_token_pressure=float(token_estimate.code_token_pressure),
            json_or_table_pressure=float(token_estimate.json_or_table_pressure),
            difficulty_risk_interaction=float(difficulty_score * risk_score),
            code_complexity_interaction=float(code_like * condition_count_val),
            cost_pressure_interaction=float(token_count_norm * cost_estimate_norm),
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
        text_features = analyze_text_prompt(prompt)
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
            "estimated_output_tokens_norm": evidence.estimated_output_tokens_norm,
            "cost_estimate_norm": evidence.cost_estimate_norm,
            "code_token_pressure": evidence.code_token_pressure,
            "json_or_table_pressure": evidence.json_or_table_pressure,
            "difficulty_risk_interaction": evidence.difficulty_risk_interaction,
            "code_complexity_interaction": evidence.code_complexity_interaction,
            "cost_pressure_interaction": evidence.cost_pressure_interaction,
            "repetition_ratio": text_features.repetition_ratio,
            "unique_char_ratio": text_features.unique_char_ratio,
            "compressed_length_norm": text_features.compressed_length_norm,
        }

    def _infer_difficulty(self, text: str, lowered: str, task_type: str, evaluation_type: str) -> float:
        if evaluation_type in {"exact_match", "numeric_check", "numeric_count"}:
            return 0.10
        if self._missing_context(text):
            return 0.65
        if self._has_hint(lowered, TASK_HINTS["architecture"]):
            return 0.85
        # Checked before the length rules so short proof/complexity requests are
        # scored by meaning rather than by character count.
        if self._has_hint(lowered, TASK_HINTS["reasoning"]):
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

    def _has_strong_difficulty_signal(self, lowered: str, evaluation_type: str) -> bool:
        """Lexical evidence strong enough to override a coarse difficulty label."""
        if evaluation_type in {"exact_match", "numeric_check", "numeric_count"}:
            return False
        return bool(
            self._has_hint(lowered, TASK_HINTS["architecture"])
            or self._has_hint(lowered, TASK_HINTS["reasoning"])
        )

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
        has_simple_math = bool(re.search(r"\d+\s*[+\-*/]\s*\d+", text))
        has_numeric_directive = any(term in text for term in ("숫자", "값만", "정답만", "몇 번", "몇개", "몇 개"))
        if evaluation_type in {"numeric_check", "numeric_count"}:
            return 1.0 if has_simple_math or has_numeric_directive or bool(re.search(r"\d", text)) else 0.0
        if evaluation_type == "exact_match":
            return 1.0 if has_simple_math or has_numeric_directive else 0.0
        return 1.0 if has_simple_math else 0.0

    def _has_hint(self, lowered: str, hints: tuple[str, ...]) -> float:
        return 1.0 if any(hint.lower() in lowered for hint in hints) else 0.0

    def _eval_type_id(self, evaluation_type: str) -> float:
        if evaluation_type not in EVALUATION_TYPES:
            evaluation_type = "unknown"
        return EVALUATION_TYPES.index(evaluation_type) / max(len(EVALUATION_TYPES) - 1, 1)

