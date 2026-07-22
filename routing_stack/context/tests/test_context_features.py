from routing_stack.context.context_features import build_context_features
from routing_stack.context.reference_detector import detect_references
from routing_stack.context.types import ConversationMessage, SessionState


def test_context_features_count_messages_and_tokens():
    messages = [ConversationMessage(role="user", content="```python\nprint(1)\n```")]
    state = SessionState(artifacts=[{"type": "code", "name": "x.py", "token_estimate": 20}])

    features, executor = build_context_features(
        "다음 코드를 분석해줘",
        messages,
        state,
        detect_references("다음 코드를 분석해줘"),
        {"estimated_input_tokens": 10, "estimated_output_tokens": 30, "missing_context": True},
    )

    assert features["conversation_message_count"] == 1
    assert features["artifact_count"] == 1
    assert features["has_code_artifact"] is True
    assert features["has_resolved_reference"] is True
    assert features["missing_context"] is False
    assert executor["resolved_references"]


def test_previous_failure_features():
    state = SessionState(previous_calls=[{"model_id": "cheap", "success": False}])
    features, _ = build_context_features("다시 해줘", [], state, detect_references("다시 해줘"), {"missing_context": False})

    assert features["previous_failure_count"] == 1
    assert features["previous_cheap_failure"] is True
