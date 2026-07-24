from __future__ import annotations

from scripts.import_korean_instruction import (
    build_prompt,
    infer_expected_min_model,
    infer_task_type,
    read_rows,
)


def test_build_prompt_combines_instruction_and_input():
    row = {"instruction": "다음을 요약해줘.", "input": "결제 오류로 출시를 연기했다."}

    assert build_prompt(row) == "다음을 요약해줘.\n\n결제 오류로 출시를 연기했다."


def test_build_prompt_reads_conversation_json():
    row = {
        "conversations": '[{"from":"system","value":"x"},{"from":"human","value":"파이썬 함수를 작성해줘."}]'
    }

    assert build_prompt(row) == "파이썬 함수를 작성해줘."


def test_korean_instruction_heuristics_map_routing_labels():
    assert infer_task_type("Python 함수를 구현해줘.") == "code"
    assert infer_expected_min_model("2 + 3의 값만 숫자만 답해줘.") == "cheap"
    assert infer_expected_min_model("멀티 리전 결제 시스템 아키텍처를 설계해줘.") == "premium"
    assert infer_expected_min_model("이 계약이 법적으로 유효한지 판단해줘.") == "abstain"


def test_read_rows_supports_jsonl(tmp_path):
    path = tmp_path / "sample.jsonl"
    path.write_text('{"instruction":"안녕"}\n{"instruction":"요약해줘"}\n', encoding="utf-8")

    rows = read_rows(path)

    assert [row["instruction"] for row in rows] == ["안녕", "요약해줘"]
