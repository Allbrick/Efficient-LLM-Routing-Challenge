from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROUTING_SCHEMA = (
    "source",
    "prompt_id",
    "prompt",
    "language",
    "task_type",
    "difficulty",
    "risk_level",
    "evaluation_type",
    "expected_min_model",
    "label_confidence",
    "license",
    "source_url",
)

MODEL_LABELS = {"cheap", "mid", "premium", "abstain", ""}
DIFFICULTIES = {"trivial", "easy", "medium", "hard", "unknown", ""}
RISK_LEVELS = {"low", "medium", "high", "unknown", ""}

PII_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4}"),
    "korean_rrn": re.compile(r"\b\d{6}[-\s]?[1-4]\d{6}\b"),
    "account_like": re.compile(r"\b\d{2,6}[-\s]\d{2,6}[-\s]\d{2,8}\b"),
}

UNSAFE_TERMS = (
    "주민등록번호",
    "계좌번호",
    "신용카드 번호",
    "password",
    "api key",
    "secret key",
)


@dataclass(frozen=True)
class DatasetSource:
    id: str
    name: str
    kind: str
    license: str
    source_url: str
    intended_use: str = ""
    storage_policy: str = ""
    risk_notes: str = ""


@dataclass
class FilterReport:
    input_rows: int = 0
    kept_rows: int = 0
    dropped_rows: int = 0
    drop_reasons: dict[str, int] = field(default_factory=dict)

    def add_drop(self, reason: str) -> None:
        self.dropped_rows += 1
        self.drop_reasons[reason] = self.drop_reasons.get(reason, 0) + 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_rows": self.input_rows,
            "kept_rows": self.kept_rows,
            "dropped_rows": self.dropped_rows,
            "drop_reasons": dict(sorted(self.drop_reasons.items())),
        }


def load_dataset_sources(path: str | Path) -> dict[str, DatasetSource]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    sources = {}
    for item in payload.get("sources", []):
        source = DatasetSource(
            id=str(item["id"]),
            name=str(item["name"]),
            kind=str(item["kind"]),
            license=str(item["license"]),
            source_url=str(item["source_url"]),
            intended_use=str(item.get("intended_use", "")),
            storage_policy=str(item.get("storage_policy", "")),
            risk_notes=str(item.get("risk_notes", "")),
        )
        sources[source.id] = source
    return sources


def validate_source_manifest(path: str | Path) -> list[str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = []
    seen = set()
    for index, item in enumerate(payload.get("sources", [])):
        prefix = f"sources[{index}]"
        for field_name in ("id", "name", "kind", "license", "source_url"):
            if not str(item.get(field_name, "")).strip():
                errors.append(f"{prefix}.{field_name} is required")
        source_id = str(item.get("id", "")).strip()
        if source_id in seen:
            errors.append(f"{prefix}.id is duplicated: {source_id}")
        seen.add(source_id)
        if str(item.get("source_url", "")).strip() and not str(item["source_url"]).startswith(("https://", "http://")):
            errors.append(f"{prefix}.source_url must be absolute HTTP URL")
    return errors


def filter_routing_rows(
    rows: list[dict[str, Any]],
    sources: dict[str, DatasetSource],
    max_prompt_chars: int = 1200,
) -> tuple[list[dict[str, str]], FilterReport]:
    report = FilterReport(input_rows=len(rows))
    kept = []
    for raw_row in rows:
        row = normalize_routing_row(raw_row, sources)
        reason = drop_reason(row, sources, max_prompt_chars=max_prompt_chars)
        if reason:
            report.add_drop(reason)
            continue
        kept.append(row)
        report.kept_rows += 1
    return kept, report


def normalize_routing_row(raw_row: dict[str, Any], sources: dict[str, DatasetSource]) -> dict[str, str]:
    source_id = str(raw_row.get("source", "") or "").strip()
    source = sources.get(source_id)
    row = {field_name: str(raw_row.get(field_name, "") or "").strip() for field_name in ROUTING_SCHEMA}
    if source is not None:
        row["license"] = row["license"] or source.license
        row["source_url"] = row["source_url"] or source.source_url
    row["expected_min_model"] = row["expected_min_model"].lower()
    row["difficulty"] = row["difficulty"].lower()
    row["risk_level"] = row["risk_level"].lower()
    row["language"] = row["language"].lower() or infer_language(row["prompt"])
    row["label_confidence"] = normalize_confidence(row["label_confidence"])
    return row


def drop_reason(row: dict[str, str], sources: dict[str, DatasetSource], max_prompt_chars: int = 1200) -> str | None:
    if row["source"] not in sources:
        return "unknown_source"
    if not row["prompt_id"]:
        return "missing_prompt_id"
    if not row["prompt"]:
        return "missing_prompt"
    if len(row["prompt"]) > max_prompt_chars:
        return "prompt_too_long"
    if not row["license"]:
        return "missing_license"
    if not row["source_url"]:
        return "missing_source_url"
    if row["expected_min_model"] not in MODEL_LABELS:
        return "invalid_expected_min_model"
    if row["difficulty"] not in DIFFICULTIES:
        return "invalid_difficulty"
    if row["risk_level"] not in RISK_LEVELS:
        return "invalid_risk_level"
    if contains_pii(row["prompt"]):
        return "pii_detected"
    if contains_unsafe_secret_term(row["prompt"]):
        return "unsafe_secret_term"
    return None


def contains_pii(text: str) -> bool:
    return any(pattern.search(text) for pattern in PII_PATTERNS.values())


def contains_unsafe_secret_term(text: str) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in UNSAFE_TERMS)


def infer_language(text: str) -> str:
    if re.search(r"[가-힣]", text):
        return "ko"
    return "en"


def normalize_confidence(value: str) -> str:
    if not value:
        return "0.5"
    try:
        number = float(value)
    except ValueError:
        return "0.5"
    return str(max(0.0, min(1.0, number)))


def read_routing_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_routing_csv(path: str | Path, rows: list[dict[str, str]]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(ROUTING_SCHEMA))
        writer.writeheader()
        writer.writerows(rows)
