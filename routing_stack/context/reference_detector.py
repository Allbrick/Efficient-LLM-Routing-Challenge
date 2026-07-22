from __future__ import annotations

from routing_stack.context.types import ReferenceSignal


TERM_GROUPS = {
    "prior_context": (
        "이거",
        "그거",
        "저거",
        "아까",
        "방금",
        "위 내용",
        "위에서",
        "앞에서",
        "이전",
        "방금 말한",
        "아까 말한",
        "this",
        "that",
        "above",
        "previous",
        "earlier",
    ),
    "artifact": (
        "첨부",
        "파일",
        "문서",
        "pdf",
        "엑셀",
        "이미지",
        "사진",
        "attached",
        "file",
        "document",
        "image",
    ),
    "code": (
        "다음 코드",
        "아래 코드",
        "이 코드",
        "코드",
        "함수",
        "클래스",
        "에러",
        "버그",
        "스택트레이스",
        "code",
        "function",
        "class",
        "stack trace",
    ),
    "design": (
        "나의 설계",
        "현재 설계",
        "이 설계",
        "설계",
        "구조",
        "아키텍처",
        "design",
        "architecture",
    ),
    "previous_result": (
        "이전 결과",
        "방금 결과",
        "다시",
        "재시도",
        "고쳐서",
        "previous result",
        "retry",
    ),
}


def detect_references(prompt: str) -> ReferenceSignal:
    """현재 요청이 이전 대화나 산출물을 참조하는지 규칙 기반으로 감지합니다."""
    text = str(prompt or "").strip()
    lowered = text.lower()
    reference_types: list[str] = []
    matched_terms: list[str] = []

    for reference_type, terms in TERM_GROUPS.items():
        for term in terms:
            if term.lower() in lowered:
                reference_types.append(reference_type)
                matched_terms.append(term)
                break

    if "code" in reference_types and "prior_context" not in reference_types and any(term in lowered for term in ("다음", "아래", "이 ")):
        reference_types.insert(0, "prior_context")
    if "design" in reference_types and "prior_context" not in reference_types and any(term in lowered for term in ("나의", "현재", "이 ")):
        reference_types.insert(0, "prior_context")

    unique_types = list(dict.fromkeys(reference_types))
    unique_terms = list(dict.fromkeys(matched_terms))
    has_reference = bool(unique_types)
    return ReferenceSignal(
        has_reference_expression=has_reference,
        reference_types=unique_types,
        needs_resolution=has_reference,
        matched_terms=unique_terms,
    )
