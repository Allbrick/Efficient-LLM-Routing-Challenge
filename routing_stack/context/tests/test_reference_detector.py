from routing_stack.context.reference_detector import detect_references


def test_detects_code_reference():
    signal = detect_references("다음 코드를 분석해줘")

    assert signal.has_reference_expression is True
    assert "code" in signal.reference_types
    assert "prior_context" in signal.reference_types


def test_detects_design_reference():
    signal = detect_references("나의 설계의 부족한 부분을 찾아줘")

    assert signal.has_reference_expression is True
    assert "design" in signal.reference_types


def test_plain_question_has_no_reference():
    signal = detect_references("API가 무엇인지 설명해줘")

    assert signal.has_reference_expression is False
    assert signal.reference_types == []


def test_detects_file_reference():
    signal = detect_references("첨부한 파일 요약해줘")

    assert signal.has_reference_expression is True
    assert "artifact" in signal.reference_types
