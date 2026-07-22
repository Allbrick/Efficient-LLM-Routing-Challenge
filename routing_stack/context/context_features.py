from __future__ import annotations

import re
from typing import Any

from routing_stack.context.state_summary import summarize_state_features
from routing_stack.context.types import ConversationMessage, ReferenceSignal, SessionState
from routing_stack.input.token_estimator import estimate_prompt_tokens


CODE_BLOCK_PATTERN = re.compile(r"```|def\s+\w+|class\s+\w+|function\s+\w+|const\s+\w+|let\s+\w+|[{};]|\=\>", re.IGNORECASE)
OUTPUT_FORMAT_TERMS = ("json", "표", "테이블", "목록", "형식", "format", "markdown", "csv")
TOOL_TERMS = ("검색", "실행", "테스트", "ocr", "pdf", "엑셀", "python", "브라우저", "search", "test")


def build_context_features(
    prompt: str,
    recent_messages: list[ConversationMessage],
    session_state: SessionState,
    reference_signal: ReferenceSignal,
    input_features: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """대화와 세션 상태를 라우터용 feature와 실행용 context로 분리합니다."""
    state_features = summarize_state_features(session_state)
    resolved = _has_resolved_reference(recent_messages, session_state, reference_signal)
    prompt_missing = bool(input_features.get("missing_context", False))
    has_reference = reference_signal.has_reference_expression
    final_missing = bool((has_reference and not resolved) or (not has_reference and prompt_missing))

    conversation_tokens = _conversation_token_estimate(recent_messages)
    artifact_tokens = _artifact_token_estimate(session_state.artifacts)
    context_tokens = conversation_tokens + int(state_features["state_summary_token_estimate"]) + artifact_tokens
    input_tokens = int(input_features.get("estimated_input_tokens", 0) or 0)
    output_tokens = int(input_features.get("estimated_output_tokens", 0) or 0)
    ref_types = set(reference_signal.reference_types)
    user_count = sum(1 for message in recent_messages if message.role == "user")
    assistant_count = sum(1 for message in recent_messages if message.role == "assistant")
    previous_failures = int(state_features["previous_failure_count"])

    router_context = {
        "has_reference_expression": has_reference,
        "has_resolved_reference": resolved,
        "missing_context": final_missing,
        "prompt_missing_context": prompt_missing,
        "requires_cross_turn_reasoning": bool(has_reference or recent_messages or session_state.summary),
        "conversation_message_count": len(recent_messages),
        "user_message_count": user_count,
        "assistant_message_count": assistant_count,
        "conversation_token_estimate": conversation_tokens,
        "artifact_token_estimate": artifact_tokens,
        "context_token_estimate": context_tokens,
        "estimated_total_input_tokens": input_tokens + context_tokens,
        "estimated_total_output_tokens": output_tokens,
        "context_token_pressure": _pressure(context_tokens, 6000),
        "history_token_pressure": _pressure(conversation_tokens, 4000),
        "artifact_token_pressure": _pressure(artifact_tokens, 6000),
        "reference_type_count": len(ref_types),
        "references_code": "code" in ref_types,
        "references_file": bool({"file", "artifact"} & ref_types),
        "references_design": "design" in ref_types,
        "references_previous_result": "previous_result" in ref_types,
        "has_artifact": bool(session_state.artifacts),
        "has_code_artifact": any(_artifact_type(item) == "code" for item in session_state.artifacts),
        "has_file_artifact": any(_artifact_type(item) in {"file", "pdf", "document", "image"} for item in session_state.artifacts),
        "retry_count": sum(1 for call in session_state.previous_calls if str(call.get("status", "")).lower() == "retry"),
        "output_format_constraint_count": _count_terms(prompt, OUTPUT_FORMAT_TERMS),
        "tool_requirement_count": _count_terms(prompt, TOOL_TERMS),
        "expected_output_complexity": _expected_output_complexity(prompt, input_features, context_tokens),
        **state_features,
    }

    executor_context = {
        "summary": session_state.summary,
        "current_target": session_state.current_target,
        "resolved_references": _resolved_references(recent_messages, session_state, reference_signal, resolved),
        "artifact_summaries": [dict(item) for item in session_state.artifacts],
    }
    return router_context, executor_context


def _has_resolved_reference(
    recent_messages: list[ConversationMessage],
    session_state: SessionState,
    reference_signal: ReferenceSignal,
) -> bool:
    if not reference_signal.has_reference_expression:
        return False
    ref_types = set(reference_signal.reference_types)
    has_messages = bool(recent_messages)
    has_summary = bool(session_state.summary)
    has_target = bool(session_state.current_target)
    has_artifact = bool(session_state.artifacts)
    has_code = _messages_have_code(recent_messages) or any(_artifact_type(item) == "code" for item in session_state.artifacts)
    has_design = has_target or has_summary or any(_contains_design_terms(message.content) for message in recent_messages)

    checks = []
    if "code" in ref_types:
        checks.append(has_code)
    if {"artifact", "file"} & ref_types:
        checks.append(has_artifact)
    if "design" in ref_types:
        checks.append(has_design)
    if "prior_context" in ref_types:
        checks.append(has_messages or has_summary)
    if "previous_result" in ref_types:
        checks.append(bool(session_state.previous_calls) or has_messages)
    return any(checks) if checks else has_messages or has_summary or has_artifact


def _conversation_token_estimate(messages: list[ConversationMessage]) -> int:
    return sum(estimate_prompt_tokens(message.content).estimated_input_tokens for message in messages)


def _artifact_token_estimate(artifacts: list[dict[str, Any]]) -> int:
    total = 0
    for artifact in artifacts:
        value = artifact.get("token_estimate", artifact.get("estimated_tokens", 0))
        try:
            total += int(value or 0)
        except (TypeError, ValueError):
            total += estimate_prompt_tokens(str(artifact.get("summary", "") or "")).estimated_input_tokens
    return total


def _resolved_references(
    recent_messages: list[ConversationMessage],
    session_state: SessionState,
    reference_signal: ReferenceSignal,
    resolved: bool,
) -> list[dict[str, Any]]:
    if not resolved:
        return []
    references = []
    for message in recent_messages[-3:]:
        references.append({"source": "conversation", "role": message.role, "type": "message", "preview": message.content[:500]})
    for artifact in session_state.artifacts[:5]:
        references.append({"source": "artifact", "type": _artifact_type(artifact), "name": artifact.get("name", ""), "preview": str(artifact.get("summary", ""))[:500]})
    if session_state.current_target and reference_signal.has_reference_expression:
        references.append({"source": "session_state", "type": "target", "preview": session_state.current_target[:500]})
    return references


def _messages_have_code(messages: list[ConversationMessage]) -> bool:
    return any(bool(CODE_BLOCK_PATTERN.search(message.content)) for message in messages)


def _contains_design_terms(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in ("설계", "구조", "아키텍처", "design", "architecture"))


def _artifact_type(artifact: dict[str, Any]) -> str:
    return str(artifact.get("type", "") or "").lower()


def _pressure(value: int, limit: int) -> float:
    return round(max(0.0, min(1.0, value / max(limit, 1))), 6)


def _count_terms(text: str, terms: tuple[str, ...]) -> int:
    lowered = str(text or "").lower()
    return sum(1 for term in terms if term.lower() in lowered)


def _expected_output_complexity(prompt: str, input_features: dict[str, Any], context_tokens: int) -> float:
    length_pressure = min(float(input_features.get("estimated_output_tokens", 0) or 0) / 1600.0, 1.0)
    context_pressure = min(context_tokens / 6000.0, 1.0)
    constraint_pressure = min((_count_terms(prompt, OUTPUT_FORMAT_TERMS) + _count_terms(prompt, TOOL_TERMS)) / 6.0, 1.0)
    return round(max(length_pressure, context_pressure, constraint_pressure), 6)
