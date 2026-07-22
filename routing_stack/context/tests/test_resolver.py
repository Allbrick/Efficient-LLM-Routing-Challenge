from routing_stack.context.resolver import resolve_context
from routing_stack.input.normalizer import normalize_input


def test_prompt_only_payload_has_default_context():
    payload = {"prompt": "안녕?"}
    context = resolve_context(payload, normalize_input(payload))

    assert context.router_context["has_reference_expression"] is False
    assert context.router_context["missing_context"] is False
    assert 0.0 <= context.context_confidence <= 1.0


def test_code_reference_resolves_from_conversation():
    payload = {
        "prompt": "다음 코드를 분석해줘",
        "conversation": [{"role": "user", "content": "```python\nprint(1)\n```"}],
    }
    context = resolve_context(payload, normalize_input(payload))

    assert context.router_context["has_resolved_reference"] is True
    assert context.router_context["missing_context"] is False


def test_code_reference_without_context_is_missing():
    payload = {"prompt": "다음 코드를 분석해줘", "conversation": []}
    context = resolve_context(payload, normalize_input(payload))

    assert context.router_context["has_resolved_reference"] is False
    assert context.router_context["missing_context"] is True


def test_design_reference_resolves_from_session_target():
    payload = {
        "prompt": "나의 설계의 부족한 부분을 찾아줘",
        "session_state": {"current_target": "task router 설계"},
    }
    context = resolve_context(payload, normalize_input(payload))

    assert context.router_context["references_design"] is True
    assert context.router_context["has_resolved_reference"] is True
