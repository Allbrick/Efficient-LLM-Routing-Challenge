from routing_stack.input import analyze_text_prompt, estimate_prompt_tokens, estimate_text_tokens


def test_text_feature_analyzer_marks_short_directive_as_simple():
    features = analyze_text_prompt("이모티콘좀 그만 써라")

    assert features.prompt_length == 11
    assert features.simple_directive is True
    assert features.code_like is False
    assert features.estimated_input_tokens > 0
    assert features.estimated_output_tokens > 0
    assert features.token_per_char > 0
    assert features.code_token_pressure == 0.0


def test_text_feature_analyzer_detects_code_like_prompt():
    features = analyze_text_prompt("다음 코드를 고쳐줘.\n```python\ndef add(a,b): return a-b\n```")

    assert features.code_like is True
    assert features.simple_directive is False
    assert features.line_count > 1
    assert features.code_token_pressure > 0


def test_token_estimator_is_local_and_deterministic():
    assert estimate_text_tokens("hello world") == estimate_text_tokens("hello world")
    assert estimate_text_tokens("") == 0


def test_token_estimator_reports_cost_pressure_features():
    code = "```python\ndef add(a, b):\n    return a + b\n```"
    table = "| name | score |\n| kim | 10 |"

    code_estimate = estimate_prompt_tokens(code)
    table_estimate = estimate_prompt_tokens(table)

    assert code_estimate.code_token_pressure > 0
    assert table_estimate.json_or_table_pressure > 0
    assert code_estimate.estimated_output_tokens >= code_estimate.estimated_input_tokens
