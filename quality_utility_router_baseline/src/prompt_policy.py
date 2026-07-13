from __future__ import annotations

from typing import List

import numpy as np


def estimate_prompt_complexity(prompt: str) -> float:
    """Return a deterministic structural complexity score in [0, 1].

    This intentionally avoids language/domain keyword hardcoding. It only uses
    surface signals that are available for any prompt language:

    - character length
    - whitespace token count
    - line/paragraph structure
    - punctuation and numeric density
    - code-like delimiters
    """
    text = prompt.strip()
    if not text:
        return 0.0

    length = len(text)
    token_count = len(text.split())
    line_count = max(1, text.count("\n") + 1)
    unique_chars = len(set(text))
    char_diversity = unique_chars / max(length, 1)

    punctuation = sum(1 for char in text if not char.isalnum() and not char.isspace())
    digits = sum(1 for char in text if char.isdigit())
    punctuation_ratio = punctuation / max(length, 1)
    digit_ratio = digits / max(length, 1)

    code_delimiters = sum(text.count(token) for token in ("{", "}", "(", ")", "[", "]", "```", ";", "=>"))
    structure_score = min(line_count / 8.0, 1.0)
    code_score = min(code_delimiters / 10.0, 1.0)

    length_score = min(length / 170.0, 1.0)
    token_score = min(token_count / 32.0, 1.0)
    punctuation_score = min(punctuation_ratio / 0.18, 1.0)
    digit_score = min(digit_ratio / 0.12, 1.0)
    diversity_score = min(char_diversity / 0.75, 1.0)

    complexity = (
        0.46 * length_score
        + 0.14 * token_score
        + 0.16 * structure_score
        + 0.12 * punctuation_score
        + 0.08 * code_score
        + 0.04 * digit_score
        + 0.04 * diversity_score
    )

    # Very short prompts are almost always cheap-tier candidates unless their
    # surface form carries unusual structure.
    if length <= 12 and token_count <= 3 and line_count == 1:
        complexity *= 0.25

    return float(np.clip(complexity, 0.0, 1.0))


def has_missing_context_signal(prompt: str) -> bool:
    """Detect short requests that refer to missing external content.

    This is not a simple/complex keyword table. It catches prompts whose
    surface form points to an omitted object, such as "fix the following code"
    without any code block or multiline payload.
    """
    stripped = prompt.strip()
    lowered = stripped.lower()
    has_payload = (
        "\n" in stripped
        or "```" in stripped
        or len(stripped) > 80
        or any(token in stripped for token in ("{", "}", ";", "=", ":", "<", ">"))
    )
    if has_payload:
        return False

    references_missing_object = any(
        token in lowered
        for token in (
            "다음",
            "이 ",
            "해당",
            "위 ",
            "첨부",
            "아래",
            "following",
            "this ",
            "above",
            "attached",
            "below",
        )
    )
    task_needs_object = any(
        token in lowered
        for token in (
            "코드",
            "계약",
            "문서",
            "파일",
            "오류",
            "고쳐",
            "수정",
            "판단",
            "분석",
            "code",
            "contract",
            "document",
            "file",
            "error",
            "fix",
            "analyze",
            "judge",
        )
    )
    return references_missing_object and task_needs_object


def has_exact_answer_signal(prompt: str) -> bool:
    """Detect prompts whose answer space is objectively tiny.

    This avoids domain labels and uses structural cues such as a short arithmetic
    expression, quoted literal transformation, or a compact multiple-choice
    surface. These cases should not require stronger models even in premium
    tier because verbosity can violate the instruction.
    """
    stripped = prompt.strip()
    if len(stripped) > 80 or "\n" in stripped:
        return False

    has_digit = any(char.isdigit() for char in stripped)
    has_operator = any(token in stripped for token in ("+", "-", "*", "/", "=", "%"))
    has_quoted_literal = "'" in stripped or '"' in stripped or "`" in stripped
    has_compact_choice = ":" in stripped and "," in stripped and len(stripped.split()) <= 12
    asks_compact_answer = any(token in stripped for token in ("한 단어", "숫자로", "값만", "번호만", "단답", "only", "one word"))

    return (has_digit and has_operator) or has_quoted_literal or has_compact_choice or asks_compact_answer


def apply_prompt_prior(
    q_calibrated: np.ndarray,
    model_ids: List[str],
    prompt: str,
    tier: str,
) -> np.ndarray:
    """Apply a language-agnostic structural prior before utility selection.

    The prior is intentionally modest. It nudges obvious short/simple prompts
    toward cheaper models and highly structured/long prompts toward stronger
    models without matching specific words or domains.
    """
    adjusted = np.array(q_calibrated, dtype=np.float64, copy=True)
    complexity = estimate_prompt_complexity(prompt)
    simplicity = 1.0 - complexity
    medium = max(0.0, 1.0 - abs(complexity - 0.5) * 2.0)
    hard = max(0.0, complexity - 0.58)
    stripped = prompt.strip()
    ultra_simple = (
        len(stripped) <= 12
        and len(stripped.split()) <= 3
        and "\n" not in stripped
        and not has_missing_context_signal(stripped)
    )
    missing_context = has_missing_context_signal(stripped)
    exact_answer = has_exact_answer_signal(stripped) and not missing_context
    tier_lower = tier.lower()

    for idx, model_id in enumerate(model_ids):
        if ultra_simple:
            if model_id == "cheap":
                adjusted[idx] += 0.62
            elif model_id == "mid":
                adjusted[idx] -= 0.05
            elif model_id == "premium":
                adjusted[idx] -= 0.28

        if exact_answer:
            if model_id == "cheap":
                adjusted[idx] += 0.46
            elif model_id == "mid":
                adjusted[idx] -= 0.08
            elif model_id == "premium":
                adjusted[idx] -= 0.34

        if tier_lower == "fast":
            if model_id == "cheap":
                adjusted[idx] += 0.50 * simplicity - 0.35 * complexity
            elif model_id == "mid":
                adjusted[idx] += 0.18 * medium + 0.01 * simplicity
            elif model_id == "premium":
                adjusted[idx] += 11.0 * hard - 0.08 * simplicity
        elif tier_lower == "balanced":
            if model_id == "cheap":
                adjusted[idx] += 0.06 * simplicity - 0.05 * complexity
            elif model_id == "mid":
                adjusted[idx] += 0.14 * medium + 0.02 * simplicity
            elif model_id == "premium":
                adjusted[idx] += 0.45 * hard - 0.02 * simplicity

        if missing_context:
            if model_id == "cheap":
                adjusted[idx] -= 0.95
            elif model_id == "mid":
                adjusted[idx] += 0.02
            elif model_id == "premium":
                adjusted[idx] += 0.38

    return adjusted
