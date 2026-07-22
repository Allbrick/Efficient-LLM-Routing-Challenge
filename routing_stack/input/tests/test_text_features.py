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


def test_text_feature_analyzer_detects_task_complexity_signals():
    conversion = analyze_text_prompt("1024MB는 몇 GB인가?")
    technical = analyze_text_prompt("Spring Boot와 Spring Framework의 차이를 비교해줘")
    advanced = analyze_text_prompt("Python으로 LRU Cache를 구현하고 시간복잡도를 증명해줘")

    assert conversion.simple_conversion is True
    assert conversion.simple_directive is True
    assert technical.technical_explanation is True
    assert technical.comparison_task is True
    assert technical.task_complexity_hint >= 0.55
    assert advanced.advanced_reasoning_task is True
    assert advanced.task_complexity_hint >= 0.85


def test_task_complexity_signals_generalize_to_unseen_domain_names():
    conceptual = analyze_text_prompt("FooDB와 BarQueue를 언제 각각 선택하는 것이 좋은가?")
    proof_like = analyze_text_prompt("XAlgo를 구현하고 정확성과 시간복잡도를 증명해줘")

    assert conceptual.technical_explanation is True
    assert conceptual.comparison_task is True
    assert conceptual.task_complexity_hint >= 0.55
    assert proof_like.advanced_reasoning_task is True
    assert proof_like.task_complexity_hint >= 0.85
