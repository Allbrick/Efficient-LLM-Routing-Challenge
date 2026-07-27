from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from routing_stack.training.external_dataset import (
    filter_routing_rows,
    load_dataset_sources,
    write_routing_csv,
)


HF_ROWS_URL = "https://datasets-server.huggingface.co/rows"


def main() -> None:
    parser = argparse.ArgumentParser(description="Download small free public dataset samples for routing training.")
    parser.add_argument("--output", default="data/external/routing_prompts.csv")
    parser.add_argument("--summary", default="data/external/external_download_summary.json")
    parser.add_argument("--manifest", default="data/external/dataset_sources.json")
    parser.add_argument("--ko_limit", type=int, default=120)
    parser.add_argument("--mt_bench_limit", type=int, default=180)
    parser.add_argument("--page_size", type=int, default=100)
    args = parser.parse_args()

    sources = load_dataset_sources(args.manifest)
    raw_rows = []
    raw_rows.extend(download_carrot_ko(args.ko_limit, args.page_size))
    raw_rows.extend(download_lmsys_mt_bench(args.mt_bench_limit, args.page_size))
    filtered_rows, report = filter_routing_rows(raw_rows, sources)
    write_routing_csv(args.output, filtered_rows)

    summary = {
        "downloaded_rows": len(raw_rows),
        "output": args.output,
        "filter_report": report.to_dict(),
        "source_counts": count_by(filtered_rows, "source"),
        "language_counts": count_by(filtered_rows, "language"),
        "expected_min_model_counts": count_by(filtered_rows, "expected_min_model"),
    }
    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def download_carrot_ko(limit: int, page_size: int) -> list[dict[str, str]]:
    rows = []
    for index, item in enumerate(iter_hf_rows("CarrotAI/ko-instruction-dataset", "default", "train", limit, page_size)):
        row = item.get("row", item)
        prompt = str(row.get("instruction") or row.get("prompt") or "").strip()
        if not prompt:
            continue
        rows.append(
            {
                "source": "carrotai_ko_instruction_dataset",
                "prompt_id": f"carrotai-ko-{index + 1:06d}",
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
        if len(rows) >= limit:
            break
    return rows


def download_lmsys_mt_bench(limit: int, page_size: int) -> list[dict[str, str]]:
    rows = []
    seen_prompts = set()
    for item in iter_hf_rows("lmsys/mt_bench_human_judgments", "default", "human", limit * 4, page_size):
        row = item.get("row", item)
        prompt = first_user_prompt(row.get("conversation_a")) or first_user_prompt(row.get("conversation_b"))
        if not prompt or prompt in seen_prompts:
            continue
        seen_prompts.add(prompt)
        expected = expected_from_mt_bench(row, prompt)
        rows.append(
            {
                "source": "lmsys_mt_bench_human_judgments",
                "prompt_id": f"lmsys-mtbench-{len(rows) + 1:06d}",
                "prompt": prompt,
                "language": "en",
                "task_type": infer_task_type(prompt),
                "difficulty": infer_difficulty(prompt),
                "risk_level": infer_risk_level(prompt),
                "evaluation_type": infer_evaluation_type(prompt),
                "expected_min_model": expected,
                "label_confidence": "0.60",
            }
        )
        if len(rows) >= limit:
            break
    return rows


def iter_hf_rows(dataset: str, config: str, split: str, limit: int, page_size: int):
    offset = 0
    remaining = limit
    while remaining > 0:
        length = min(max(page_size, 1), 100, remaining)
        payload = fetch_hf_rows(dataset, config, split, offset, length)
        rows = payload.get("rows", [])
        if not rows:
            break
        for row in rows:
            yield row
        if len(rows) < length:
            break
        offset += length
        remaining -= length
        time.sleep(0.1)


def fetch_hf_rows(dataset: str, config: str, split: str, offset: int, length: int) -> dict[str, Any]:
    query = urlencode(
        {
            "dataset": dataset,
            "config": config,
            "split": split,
            "offset": offset,
            "length": length,
        }
    )
    url = f"{HF_ROWS_URL}?{query}"
    try:
        with urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"failed to download {url}: {exc}") from exc


def first_user_prompt(conversation: Any) -> str:
    if isinstance(conversation, str):
        try:
            conversation = json.loads(conversation)
        except json.JSONDecodeError:
            return conversation.strip()
    if not isinstance(conversation, list):
        return ""
    for item in conversation:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or item.get("from") or "").lower()
        if role in {"user", "human"}:
            return str(item.get("content") or item.get("value") or "").strip()
    return ""


def expected_from_mt_bench(row: dict[str, Any], prompt: str) -> str:
    model_a = str(row.get("model_a", "")).lower()
    model_b = str(row.get("model_b", "")).lower()
    winner = str(row.get("winner", "")).lower()
    strong_models = {"gpt-4", "claude-v1"}
    if any(model in strong_models for model in (model_a, model_b)):
        if winner in {"model_a", "model_b"}:
            winning_model = model_a if winner == "model_a" else model_b
            if winning_model in strong_models and infer_difficulty(prompt) != "easy":
                return "premium"
        if infer_difficulty(prompt) == "hard":
            return "premium"
    if infer_difficulty(prompt) == "easy":
        return "cheap"
    return "mid"


def infer_task_type(prompt: str) -> str:
    lowered = prompt.lower()
    if any(term in lowered for term in ("code", "function", "python", "javascript", "typescript", "코드", "함수")):
        return "code"
    if any(term in lowered for term in ("summarize", "summary", "요약", "정리")):
        return "summary"
    if any(term in lowered for term in ("translate", "번역")):
        return "translation"
    if any(term in lowered for term in ("json", "csv", "table", "표")):
        return "data_transform"
    if any(term in lowered for term in ("design", "architecture", "system", "설계", "아키텍처", "시스템")):
        return "architecture"
    if any(term in lowered for term in ("legal", "medical", "contract", "법률", "의료", "계약")):
        return "sensitive_advice"
    return "general_instruction"


def infer_difficulty(prompt: str) -> str:
    lowered = prompt.lower()
    if len(prompt) <= 60 and not any(term in lowered for term in ("design", "architecture", "code", "legal", "medical")):
        return "easy"
    if any(term in lowered for term in ("distributed", "architecture", "security", "concurrency", "failure", "audit", "아키텍처", "보안", "동시성", "장애", "감사")):
        return "hard"
    if len(prompt) >= 260 or prompt.count("\n") >= 3:
        return "hard"
    return "medium"


def infer_risk_level(prompt: str) -> str:
    lowered = prompt.lower()
    if any(term in lowered for term in ("legal", "medical", "diagnosis", "investment", "privacy", "security", "법률", "의료", "투자", "개인정보", "보안")):
        return "high"
    if any(term in lowered for term in ("payment", "permission", "audit", "failure", "결제", "권한", "감사", "장애")):
        return "medium"
    return "low"


def infer_evaluation_type(prompt: str) -> str:
    lowered = prompt.lower()
    if any(term in lowered for term in ("number only", "calculate", "몇 개", "몇 번", "계산", "숫자만")):
        return "numeric_check"
    if any(term in lowered for term in ("json", "csv")):
        return "exact_json"
    if any(term in lowered for term in ("code", "function", "implement", "코드", "함수", "구현")):
        return "unit_test"
    if any(term in lowered for term in ("design", "architecture", "compare", "analyze", "설계", "아키텍처", "분석")):
        return "rubric_check"
    if any(term in lowered for term in ("summarize", "bullet", "translate", "요약", "불릿", "번역")):
        return "constraint_check"
    return "rubric_check"


def infer_expected_min_model(prompt: str) -> str:
    risk = infer_risk_level(prompt)
    difficulty = infer_difficulty(prompt)
    task_type = infer_task_type(prompt)
    if risk == "high" and any(term in prompt.lower() for term in ("diagnose", "valid", "guarantee", "진단", "유효", "무효", "보장")):
        return "abstain"
    if difficulty == "hard" or task_type in {"architecture", "sensitive_advice"}:
        return "premium"
    if task_type in {"code", "data_transform"} or difficulty == "medium":
        return "mid"
    return "cheap"


def count_by(rows: list[dict[str, str]], key: str) -> dict[str, int]:
    counts = {}
    for row in rows:
        value = str(row.get(key, "") or "<empty>")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    main()
