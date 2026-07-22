from __future__ import annotations

from typing import Any

from routing_stack.context.context_features import build_context_features
from routing_stack.context.reference_detector import detect_references
from routing_stack.context.state_summary import parse_session_state
from routing_stack.context.types import ConversationMessage, RoutingContext
from routing_stack.input.normalizer import NormalizedInput


MAX_RECENT_MESSAGES = 10
MAX_MESSAGE_CHARS = 4000


def resolve_context(payload: dict[str, Any], normalized_input: NormalizedInput) -> RoutingContext:
    """현재 요청과 주변 상태를 Task Router가 사용할 context로 해석합니다."""
    prompt = normalized_input.text
    messages = _parse_messages(payload.get("conversation"))
    session_state = parse_session_state(payload)
    reference_signal = detect_references(prompt)
    router_context, executor_context = build_context_features(
        prompt=prompt,
        recent_messages=messages,
        session_state=session_state,
        reference_signal=reference_signal,
        input_features=normalized_input.router_features,
    )
    confidence = _context_confidence(prompt, messages, session_state, router_context, reference_signal)
    router_context["context_confidence"] = confidence
    return RoutingContext(
        current_prompt=prompt,
        recent_messages=messages,
        session_state=session_state,
        reference_signal=reference_signal,
        router_context=router_context,
        executor_context=executor_context,
        context_confidence=confidence,
    )


def _parse_messages(raw_messages: Any) -> list[ConversationMessage]:
    if not isinstance(raw_messages, list):
        return []
    parsed = []
    for item in raw_messages[-MAX_RECENT_MESSAGES:]:
        if not isinstance(item, dict):
            continue
        content = str(item.get("content", "") or "").strip()
        if not content:
            continue
        parsed.append(
            ConversationMessage(
                role=str(item.get("role", "user") or "user").strip().lower(),
                content=content[:MAX_MESSAGE_CHARS],
                created_at=str(item.get("created_at")) if item.get("created_at") is not None else None,
            )
        )
    return parsed


def _context_confidence(prompt: str, messages: list[ConversationMessage], session_state, router_context: dict[str, Any], reference_signal) -> float:
    confidence = 0.50
    if not reference_signal.has_reference_expression:
        confidence += 0.20
    if router_context.get("has_resolved_reference"):
        confidence += 0.25
    if session_state.current_target:
        confidence += 0.10
    if session_state.artifacts:
        confidence += 0.10
    if messages:
        confidence += 0.05
    if reference_signal.has_reference_expression and not router_context.get("has_resolved_reference"):
        confidence -= 0.20
    if len(prompt.strip()) <= 40 and reference_signal.has_reference_expression:
        confidence -= 0.10
    return round(max(0.0, min(1.0, confidence)), 6)
