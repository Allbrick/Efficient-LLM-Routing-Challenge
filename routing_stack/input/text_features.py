from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from routing_stack.input.token_estimator import estimate_prompt_tokens


_CODE_PATTERN = re.compile(
    r"(```|def\s+\w+|class\s+\w+|function\s+\w+|const\s+\w+|let\s+\w+|"
    r"import\s+\w+|SELECT\s+|CREATE\s+TABLE|[{};]|\=\>)",
    re.IGNORECASE,
)
_LIST_PATTERN = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+", re.MULTILINE)
_MISSING_CONTEXT_POINTERS = ("다음", "해당", "위", "아래", "첨부", "this", "above", "below", "attached")
_MISSING_CONTEXT_TASKS = ("고쳐", "수정", "분석", "검토", "판단", "fix", "analyze", "review", "judge")


@dataclass(frozen=True)
class TextFeatures:
    prompt_length: int
    whitespace_token_count: int
    estimated_input_tokens: int
    estimated_output_tokens: int
    token_per_char: float
    code_token_pressure: float
    json_or_table_pressure: float
    line_count: int
    sentence_count: int
    punctuation_ratio: float
    digit_ratio: float
    char_diversity: float
    code_like: bool
    list_like: bool
    missing_context: bool
    simple_directive: bool

    def to_dict(self) -> dict:
        return asdict(self)


def analyze_text_prompt(prompt: str) -> TextFeatures:
    """라우터들이 공통으로 참조할 수 있는 텍스트 입력 특징을 추출합니다."""
    text = str(prompt)
    stripped = text.strip()
    length = len(stripped)
    whitespace_tokens = len(stripped.split())
    line_count = max(1, stripped.count("\n") + 1) if stripped else 0
    punctuation = sum(1 for char in stripped if not char.isalnum() and not char.isspace())
    digits = sum(1 for char in stripped if char.isdigit())
    unique_chars = len(set(stripped))
    code_like = bool(_CODE_PATTERN.search(stripped))
    list_like = bool(_LIST_PATTERN.search(stripped))
    missing_context = _has_missing_context(stripped)
    token_estimate = estimate_prompt_tokens(stripped)
    simple_directive = (
        0 < length <= 40
        and line_count == 1
        and not code_like
        and not list_like
        and not missing_context
        and punctuation <= 2
    )

    return TextFeatures(
        prompt_length=length,
        whitespace_token_count=whitespace_tokens,
        estimated_input_tokens=token_estimate.estimated_input_tokens,
        estimated_output_tokens=token_estimate.estimated_output_tokens,
        token_per_char=token_estimate.token_per_char,
        code_token_pressure=token_estimate.code_token_pressure,
        json_or_table_pressure=token_estimate.json_or_table_pressure,
        line_count=line_count,
        sentence_count=sum(stripped.count(mark) for mark in (".", "!", "?")),
        punctuation_ratio=round(punctuation / max(length, 1), 6),
        digit_ratio=round(digits / max(length, 1), 6),
        char_diversity=round(unique_chars / max(length, 1), 6),
        code_like=code_like,
        list_like=list_like,
        missing_context=missing_context,
        simple_directive=simple_directive,
    )


def _has_missing_context(text: str) -> bool:
    if not text or len(text) > 100:
        return False

    lowered = text.lower()
    has_pointer = any(term in lowered for term in _MISSING_CONTEXT_POINTERS)
    has_task = any(term in lowered for term in _MISSING_CONTEXT_TASKS)
    has_payload = "\n" in text or "```" in text or bool(_CODE_PATTERN.search(text))
    return bool(has_pointer and has_task and not has_payload)
