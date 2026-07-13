from __future__ import annotations

from typing import List

import numpy as np


SIMPLE_MARKERS = [
    "한 문장",
    "무엇인지",
    "요약",
    "번역",
    "평균 속도",
    "간단",
    "짧은",
    "쉬운",
    "정의",
    "one sentence",
    "summarize",
    "translate",
]

COMPLEX_MARKERS = [
    "설계",
    "아키텍처",
    "프로세스",
    "알고리즘",
    "응급",
    "법적",
    "의학",
    "의료",
    "복합",
    "파이프라인",
    "보장",
    "멀티테넌트",
    "대용량",
    "디지털 트윈",
    "분산",
    "동시성",
    "architecture",
    "algorithm",
    "emergency",
    "pipeline",
]


def estimate_prompt_complexity(prompt: str) -> float:
    """Return a deterministic prompt complexity score in [0, 1]."""
    text = prompt.lower()
    length = len(prompt)
    token_count = len(prompt.split())

    score = 0.2
    if length > 70 or token_count > 12:
        score += 0.14
    if length > 130 or token_count > 22:
        score += 0.18
    if length > 230 or token_count > 38:
        score += 0.16

    score += 0.13 * sum(1 for marker in COMPLEX_MARKERS if marker.lower() in text)
    score -= 0.16 * sum(1 for marker in SIMPLE_MARKERS if marker.lower() in text)

    if "```" in prompt or "def " in text or "function " in text:
        score += 0.08
    if "단계별" in prompt or "비교" in prompt:
        score += 0.07

    return float(np.clip(score, 0.0, 1.0))


def apply_prompt_prior(
    q_calibrated: np.ndarray,
    model_ids: List[str],
    prompt: str,
    tier: str,
) -> np.ndarray:
    """Adjust calibrated quality with a prompt-level routing prior.

    Fast tier should still be able to escalate to premium for hard prompts. The
    prior therefore has three regions:

    - simple: cheap gets a boost
    - medium: mid gets a boost
    - complex: premium gets enough boost to overcome fast-tier cost pressure
    """
    adjusted = np.array(q_calibrated, dtype=np.float64, copy=True)
    complexity = estimate_prompt_complexity(prompt)
    simplicity = 1.0 - complexity
    medium = max(0.0, 1.0 - abs(complexity - 0.5) * 2.0)
    hard = max(0.0, complexity - 0.55)
    tier_lower = tier.lower()

    for idx, model_id in enumerate(model_ids):
        if tier_lower == "fast":
            if model_id == "cheap":
                adjusted[idx] += 0.36 * simplicity - 0.24 * complexity
            elif model_id == "mid":
                adjusted[idx] += 0.16 * medium + 0.04 * simplicity
            elif model_id == "premium":
                adjusted[idx] += 5.2 * hard - 0.08 * simplicity
        elif tier_lower == "balanced":
            if model_id == "cheap":
                adjusted[idx] += 0.08 * simplicity - 0.06 * complexity
            elif model_id == "mid":
                adjusted[idx] += 0.12 * medium + 0.04 * simplicity
            elif model_id == "premium":
                adjusted[idx] += 0.35 * hard - 0.02 * simplicity

    return adjusted
