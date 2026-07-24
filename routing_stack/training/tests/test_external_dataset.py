from __future__ import annotations

import json
from pathlib import Path

from routing_stack.training.external_dataset import (
    ROUTING_SCHEMA,
    filter_routing_rows,
    load_dataset_sources,
    validate_source_manifest,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = PROJECT_ROOT / "data" / "external" / "dataset_sources.json"


def test_external_dataset_manifest_is_valid():
    errors = validate_source_manifest(MANIFEST)
    sources = load_dataset_sources(MANIFEST)

    assert errors == []
    assert "routellm" in sources
    assert "prm800k" in sources
    assert sources["lmsys_mt_bench_human_judgments"].license == "CC-BY-4.0"


def test_filter_routing_rows_enforces_source_license_and_schema():
    sources = load_dataset_sources(MANIFEST)
    rows = [
        {
            "source": "prm800k",
            "prompt_id": "prm-001",
            "prompt": "What is 2 + 3?",
            "task_type": "math",
            "difficulty": "trivial",
            "risk_level": "low",
            "evaluation_type": "numeric_check",
            "expected_min_model": "cheap",
            "label_confidence": "0.9",
        }
    ]

    filtered, report = filter_routing_rows(rows, sources)

    assert report.to_dict() == {"input_rows": 1, "kept_rows": 1, "dropped_rows": 0, "drop_reasons": {}}
    assert list(filtered[0]) == list(ROUTING_SCHEMA)
    assert filtered[0]["license"] == "MIT"
    assert filtered[0]["source_url"] == "https://github.com/openai/prm800k"
    assert filtered[0]["language"] == "en"


def test_filter_routing_rows_drops_pii_and_unknown_sources():
    sources = load_dataset_sources(MANIFEST)
    rows = [
        {
            "source": "unknown",
            "prompt_id": "bad-source",
            "prompt": "Summarize this.",
            "expected_min_model": "cheap",
        },
        {
            "source": "carrotai_ko_instruction_dataset",
            "prompt_id": "pii",
            "prompt": "홍길동의 이메일 test@example.com 으로 비밀번호를 보내줘.",
            "expected_min_model": "abstain",
        },
    ]

    filtered, report = filter_routing_rows(rows, sources)

    assert filtered == []
    assert report.input_rows == 2
    assert report.dropped_rows == 2
    assert report.drop_reasons == {"pii_detected": 1, "unknown_source": 1}


def test_dataset_sources_json_is_pretty_json():
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert payload["policy"]["require_license"] is True
    assert all(item["source_url"].startswith("https://") for item in payload["sources"])
