from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from routing_stack.training.external_dataset import (
    filter_routing_rows,
    load_dataset_sources,
    write_routing_csv,
)


DEFAULT_SOURCE = "carrotai_ko_instruction_dataset"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a local Korean instruction CSV/JSONL export into external routing prompt rows."
    )
    parser.add_argument("--input", required=True, help="Local CSV or JSONL file exported from a Korean instruction dataset.")
    parser.add_argument("--output", default="data/external/routing_prompts.csv")
    parser.add_argument("--manifest", default="data/external/dataset_sources.json")
    parser.add_argument("--report", default="data/external/filter_report.json")
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--limit", type=int, default=0, help="Maximum rows to import. 0 means no limit.")
    parser.add_argument("--max_prompt_chars", type=int, default=1200)
    args = parser.parse_args()

    sources = load_dataset_sources(args.manifest)
    raw_rows = read_rows(args.input)
    routing_rows = []
    for index, row in enumerate(raw_rows):
        prompt = build_prompt(row)
        if not prompt:
            continue
        routing_rows.append(
            {
                "source": args.source,
                "prompt_id": f"{args.source}-{index + 1:06d}",
                "prompt": prompt,
                "language": "ko",
                "task_type": infer_task_type(prompt),
                "difficulty": infer_difficulty(prompt),
                "risk_level": infer_risk_level(prompt),
                "evaluation_type": infer_evaluation_type(prompt),
                "expected_min_model": infer_expected_min_model(prompt),
                "label_confidence": "0.55",
            }
        )
        if args.limit and len(routing_rows) >= args.limit:
            break

    filtered_rows, report = filter_routing_rows(routing_rows, sources, max_prompt_chars=args.max_prompt_chars)
    write_routing_csv(args.output, filtered_rows)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))


def read_rows(path: str | Path) -> list[dict[str, Any]]:
    input_path = Path(path)
    if input_path.suffix.lower() == ".jsonl":
        rows = []
        for line in input_path.read_text(encoding="utf-8-sig").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_prompt(row: dict[str, Any]) -> str:
    direct = first_nonempty(row, ("prompt", "instruction", "question", "query", "text"))
    extra_input = first_nonempty(row, ("input", "context", "source_text"))
    if not direct:
        conversations = row.get("conversations") or row.get("messages")
        direct = first_user_message(conversations)
    if not direct:
        return ""
    if extra_input and extra_input not in direct:
        return f"{direct}\n\n{extra_input}".strip()
    return str(direct).strip()


def first_nonempty(row: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def first_user_message(conversations: Any) -> str:
    if isinstance(conversations, str):
        try:
            conversations = json.loads(conversations)
        except json.JSONDecodeError:
            return conversations.strip()
    if not isinstance(conversations, list):
        return ""
    for item in conversations:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or item.get("from") or "").lower()
        if role in {"user", "human"}:
            return str(item.get("content") or item.get("value") or "").strip()
    return ""


def infer_task_type(prompt: str) -> str:
    if any(term in prompt for term in ("코드", "함수", "파이썬", "자바스크립트", "TypeScript", "JavaScript")):
        return "code"
    if any(term in prompt for term in ("요약", "정리", "불릿")):
        return "summary"
    if any(term in prompt for term in ("번역", "영어로", "한국어로")):
        return "translation"
    if any(term in prompt for term in ("JSON", "CSV", "표", "스키마")):
        return "data_transform"
    if any(term in prompt for term in ("설계", "아키텍처", "시스템")):
        return "architecture"
    if any(term in prompt for term in ("계약", "법률", "법적", "의료", "치료", "투자")):
        return "sensitive_advice"
    return "general_instruction"


def infer_difficulty(prompt: str) -> str:
    if len(prompt) <= 40 and not any(term in prompt for term in ("설계", "비교", "코드", "계약", "의료")):
        return "easy"
    if any(term in prompt for term in ("분산", "아키텍처", "보안", "동시성", "정합성", "장애", "감사")):
        return "hard"
    if len(prompt) >= 220 or prompt.count("\n") >= 3:
        return "hard"
    return "medium"


def infer_risk_level(prompt: str) -> str:
    if any(term in prompt for term in ("계약", "법률", "법적", "의료", "치료", "진단", "투자", "개인정보", "보안")):
        return "high"
    if any(term in prompt for term in ("장애", "결제", "권한", "데이터 삭제", "감사")):
        return "medium"
    return "low"


def infer_evaluation_type(prompt: str) -> str:
    if any(term in prompt for term in ("숫자만", "값만", "몇 개", "몇 번", "계산")):
        return "numeric_check"
    if any(term in prompt for term in ("JSON", "CSV")):
        return "exact_json"
    if any(term in prompt for term in ("코드", "함수", "구현")):
        return "unit_test"
    if any(term in prompt for term in ("설계", "아키텍처", "비교", "분석")):
        return "rubric_check"
    if any(term in prompt for term in ("요약", "불릿", "번역")):
        return "constraint_check"
    return "rubric_check"


def infer_expected_min_model(prompt: str) -> str:
    risk = infer_risk_level(prompt)
    difficulty = infer_difficulty(prompt)
    task_type = infer_task_type(prompt)
    if risk == "high" and any(term in prompt for term in ("판단", "정해", "진단", "유효", "무효", "보장")):
        return "abstain"
    if difficulty == "hard" or task_type in {"architecture", "sensitive_advice"}:
        return "premium"
    if task_type in {"code", "data_transform"} or difficulty == "medium":
        return "mid"
    return "cheap"


if __name__ == "__main__":
    main()
