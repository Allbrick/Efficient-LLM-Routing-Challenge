from __future__ import annotations

import json

from scripts.build_external_routing_dataset import build_external_eval_specs, summarize_external_rows


def test_build_external_eval_specs_preserves_source_metadata():
    rows = [
        {
            "source": "carrotai_ko_instruction_dataset",
            "prompt_id": "ko-001",
            "prompt": "다음을 요약해줘.",
            "task_type": "summary",
            "difficulty": "easy",
            "risk_level": "low",
            "evaluation_type": "constraint_check",
            "expected_min_model": "cheap",
            "label_confidence": "0.55",
            "license": "MIT",
            "source_url": "https://huggingface.co/datasets/CarrotAI/ko-instruction-dataset",
        }
    ]

    specs = build_external_eval_specs(rows)

    assert specs[0]["prompt_id"] == "ko-001"
    assert specs[0]["expected_min_model"] == "cheap"
    payload = json.loads(specs[0]["test_spec"])
    assert payload["source"] == "carrotai_ko_instruction_dataset"
    assert payload["license"] == "MIT"
    assert payload["label_confidence"] == "0.55"


def test_build_external_eval_specs_drops_duplicate_prompt_ids():
    rows = [
        {"prompt_id": "dup", "prompt": "A", "expected_min_model": "cheap"},
        {"prompt_id": "dup", "prompt": "B", "expected_min_model": "premium"},
    ]

    specs = build_external_eval_specs(rows)

    assert len(specs) == 1
    assert specs[0]["prompt"] == "A"


def test_summarize_external_rows_counts_labels_and_sources():
    rows = [
        {"source": "a", "license": "MIT", "prompt_id": "1"},
        {"source": "a", "license": "MIT", "prompt_id": "2"},
        {"source": "b", "license": "CC-BY-4.0", "prompt_id": "3"},
    ]
    specs = [
        {"expected_min_model": "cheap", "difficulty": "easy", "risk_level": "low", "evaluation_type": "numeric_check"},
        {"expected_min_model": "premium", "difficulty": "hard", "risk_level": "high", "evaluation_type": "rubric_check"},
    ]

    summary = summarize_external_rows(rows, specs)

    assert summary["input_rows"] == 3
    assert summary["spec_rows"] == 2
    assert summary["source_counts"] == {"a": 2, "b": 1}
    assert summary["expected_min_model_counts"] == {"cheap": 1, "premium": 1}
