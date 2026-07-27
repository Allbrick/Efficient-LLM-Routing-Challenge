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
_LATIN_TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9+#./-]{1,}")
_ACRONYM_PATTERN = re.compile(r"\b[A-Z0-9]{2,}(?:/[A-Z0-9]{2,})?\b")
_COMPARISON_TERMS = ("차이", "비교", "각각", "언제", "상황", "장단점", "공통점", "선택", "vs", "versus", "compare", "difference")
_EXPLANATION_TERMS = ("설명", "이유", "필요", "흐름", "단계", "원리", "개념", "사례", "문제점", "when", "why", "explain")
_DESIGN_TERMS = ("설계", "전략", "파이프라인", "아키텍처", "구성", "제안", "design", "architecture", "pipeline", "strategy")
_ADVANCED_TERMS = (
    "구현",
    "증명",
    "분석하여",
    "분석해서",
    "병목",
    "최적화",
    "복잡도",
    "논문",
    "핵심 기여",
    "한계",
    "후속 연구",
    "실험",
    "검증",
    "implement",
    "prove",
    "proof",
    "analyze and",
    "bottleneck",
    "optimize",
    "paper",
    "research",
)
_SIMPLE_CONVERSION_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(mb|gb|kb|달러|usd|원|만원|cm|mm|km|m)|몇\s*(gb|mb|원|달러)",
    re.IGNORECASE,
)


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
    simple_conversion: bool
    compressed_prompt: str
    compressed_prompt_length: int
    repetition_ratio: float
    unique_char_ratio: float
    compressed_length_norm: float
    technical_explanation: bool
    comparison_task: bool
    design_task: bool
    advanced_reasoning_task: bool
    task_complexity_hint: float

    def to_dict(self) -> dict:
        return asdict(self)


def analyze_text_prompt(prompt: str) -> TextFeatures:
    """라우터들이 공통으로 참조할 수 있는 텍스트 입력 특징을 추출합니다."""
    text = str(prompt)
    stripped = text.strip()
    compressed = compress_repeated_spans(stripped)
    length = len(stripped)
    whitespace_tokens = len(stripped.split())
    line_count = max(1, stripped.count("\n") + 1) if stripped else 0
    punctuation = sum(1 for char in stripped if not char.isalnum() and not char.isspace())
    digits = sum(1 for char in stripped if char.isdigit())
    unique_chars = len(set(stripped))
    latin_token_count = _latin_token_count(stripped)
    acronym_count = _acronym_count(stripped)
    code_like = bool(_CODE_PATTERN.search(stripped))
    list_like = bool(_LIST_PATTERN.search(stripped))
    missing_context = _has_missing_context(stripped)
    simple_conversion = _is_simple_conversion(stripped)
    comparison_task = _has_any(stripped, _COMPARISON_TERMS)
    explanation_task = _has_any(stripped, _EXPLANATION_TERMS)
    design_task = _has_any(stripped, _DESIGN_TERMS)
    advanced_reasoning_task = _is_advanced_reasoning_task(stripped)
    technical_explanation = _is_domain_explanation_task(
        latin_token_count=latin_token_count,
        acronym_count=acronym_count,
        explanation_task=explanation_task,
        comparison_task=comparison_task,
        design_task=design_task,
        advanced_reasoning_task=advanced_reasoning_task,
        code_like=code_like,
    )
    complexity_hint = _task_complexity_hint(
        technical_explanation=technical_explanation,
        comparison_task=comparison_task,
        design_task=design_task,
        advanced_reasoning_task=advanced_reasoning_task,
        simple_conversion=simple_conversion,
    )
    token_estimate = estimate_prompt_tokens(stripped)
    simple_directive = (
        0 < length <= 40
        and line_count == 1
        and not code_like
        and not list_like
        and not missing_context
        and not technical_explanation
        and not comparison_task
        and not design_task
        and not advanced_reasoning_task
        and punctuation <= 2
    ) or simple_conversion

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
        simple_conversion=simple_conversion,
        compressed_prompt=compressed,
        compressed_prompt_length=len(compressed),
        repetition_ratio=_repetition_ratio(stripped, compressed),
        unique_char_ratio=round(unique_chars / max(length, 1), 6),
        compressed_length_norm=round(min(len(compressed) / 500.0, 1.0), 6),
        technical_explanation=technical_explanation,
        comparison_task=comparison_task,
        design_task=design_task,
        advanced_reasoning_task=advanced_reasoning_task,
        task_complexity_hint=complexity_hint,
    )


def compress_repeated_spans(text: str, min_unit_chars: int = 6, max_unit_chars: int = 120) -> str:
    stripped = str(text or "").strip()
    if not stripped:
        return ""
    compact = re.sub(r"\s+", " ", stripped)
    collapsed = _collapse_adjacent_repeats(compact, min_unit_chars, max_unit_chars)
    if len(collapsed) < len(compact):
        return collapsed.strip()
    return compact


def _collapse_adjacent_repeats(text: str, min_unit_chars: int, max_unit_chars: int) -> str:
    current = text
    max_unit = min(max_unit_chars, max(len(current) // 2, min_unit_chars))
    for unit_len in range(max_unit, min_unit_chars - 1, -1):
        pattern = re.compile(rf"(.{{{unit_len}}})\1+", re.DOTALL)

        def replace(match: re.Match) -> str:
            unit = match.group(1)
            if len(set(unit.strip())) < 2:
                return match.group(0)
            return unit

        updated = pattern.sub(replace, current)
        if updated != current:
            current = updated
    return current


def _repetition_ratio(original: str, compressed: str) -> float:
    original_len = len(original)
    if original_len <= 0:
        return 0.0
    return round(max(0.0, 1.0 - (len(compressed) / original_len)), 6)


def _has_missing_context(text: str) -> bool:
    if not text or len(text) > 100:
        return False

    lowered = text.lower()
    has_pointer = any(term in lowered for term in _MISSING_CONTEXT_POINTERS)
    has_task = any(term in lowered for term in _MISSING_CONTEXT_TASKS)
    has_payload = "\n" in text or "```" in text or bool(_CODE_PATTERN.search(text))
    return bool(has_pointer and has_task and not has_payload)


def _is_simple_conversion(text: str) -> bool:
    lowered = text.lower()
    has_conversion = bool(_SIMPLE_CONVERSION_PATTERN.search(lowered))
    asks_rough_amount = any(term in lowered for term in ("대충", "얼마", "몇", "환산", "convert"))
    return bool(has_conversion and asks_rough_amount and len(text) <= 60)


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def _latin_token_count(text: str) -> int:
    return len(_LATIN_TOKEN_PATTERN.findall(text))


def _acronym_count(text: str) -> int:
    return len(_ACRONYM_PATTERN.findall(text))


def _is_domain_explanation_task(
    *,
    latin_token_count: int,
    acronym_count: int,
    explanation_task: bool,
    comparison_task: bool,
    design_task: bool,
    advanced_reasoning_task: bool,
    code_like: bool,
) -> bool:
    has_domain_marker = latin_token_count >= 1 or acronym_count >= 1 or code_like
    has_conceptual_operation = explanation_task or comparison_task or design_task or advanced_reasoning_task
    return bool(has_domain_marker and has_conceptual_operation)


def _is_advanced_reasoning_task(text: str) -> bool:
    lowered = text.lower()
    if _has_any(lowered, _ADVANCED_TERMS):
        return True
    operation_count = sum(
        1
        for terms in (_COMPARISON_TERMS, _EXPLANATION_TERMS, _DESIGN_TERMS)
        if _has_any(lowered, terms)
    )
    return operation_count >= 3 and len(text) >= 80


def _task_complexity_hint(
    *,
    technical_explanation: bool,
    comparison_task: bool,
    design_task: bool,
    advanced_reasoning_task: bool,
    simple_conversion: bool,
) -> float:
    if simple_conversion:
        return 0.05
    score = 0.0
    if technical_explanation:
        score = max(score, 0.45)
    if comparison_task:
        score = max(score, 0.55)
    if design_task:
        score = max(score, 0.65)
    if advanced_reasoning_task:
        score = max(score, 0.85)
    return round(score, 6)
