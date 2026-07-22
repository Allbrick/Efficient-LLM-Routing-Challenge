from __future__ import annotations

from typing import Any

from routing_stack.context.types import SessionState
from routing_stack.input.token_estimator import estimate_prompt_tokens


def parse_session_state(payload: dict[str, Any]) -> SessionState:
    """payload의 세션 상태와 호출 이력을 정규화합니다."""
    raw_state = payload.get("session_state") or {}
    if not isinstance(raw_state, dict):
        raw_state = {}

    previous_calls = []
    previous_calls.extend(_as_list(raw_state.get("previous_calls")))
    previous_calls.extend(_as_list(payload.get("call_history")))

    return SessionState(
        summary=str(raw_state.get("summary", "") or "").strip(),
        current_target=str(raw_state.get("current_target", "") or "").strip(),
        constraints=dict(raw_state.get("constraints") or {}),
        artifacts=[dict(item) for item in _as_list(raw_state.get("artifacts")) if isinstance(item, dict)],
        previous_calls=_dedupe_calls(previous_calls),
    )


def summarize_state_features(session_state: SessionState) -> dict[str, Any]:
    summary_tokens = estimate_prompt_tokens(session_state.summary).estimated_input_tokens if session_state.summary else 0
    previous_failures = [call for call in session_state.previous_calls if _is_failed_call(call)]
    return {
        "state_summary_length": len(session_state.summary),
        "state_summary_token_estimate": summary_tokens,
        "has_current_target": bool(session_state.current_target),
        "constraint_count": len(session_state.constraints),
        "artifact_count": len(session_state.artifacts),
        "previous_call_count": len(session_state.previous_calls),
        "previous_failure_count": len(previous_failures),
        "previous_cheap_failure": any(str(call.get("model_id", "")).lower() == "cheap" for call in previous_failures),
        "previous_mid_failure": any(str(call.get("model_id", "")).lower() == "mid" for call in previous_failures),
    }


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _dedupe_calls(calls: list[Any]) -> list[dict[str, Any]]:
    deduped = []
    seen = set()
    for call in calls:
        if not isinstance(call, dict):
            continue
        item = dict(call)
        key = (
            str(item.get("model_id", "")),
            str(item.get("reason", "")),
            str(item.get("created_at", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _is_failed_call(call: dict[str, Any]) -> bool:
    if "success" in call:
        return not bool(call.get("success"))
    status = str(call.get("status", "")).lower()
    return status in {"failed", "error", "retry", "rejected"}
