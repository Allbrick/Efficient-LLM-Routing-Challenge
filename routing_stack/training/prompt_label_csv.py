from __future__ import annotations

import csv
import io
from pathlib import Path


LEGACY_LABEL_SCORES = {"cheap": 20.0, "mid": 55.0, "premium": 85.0}
PROMPT_ALIASES = ("prompt", "프롬프트", "질문", "입력", "input", "user_prompt", "question")
SCORE_ALIASES = ("routing_score", "score", "router_score", "route_score", "점수", "라우팅점수")
LEGACY_LABEL_ALIASES = ("정답", "label", "answer", "expected", "예상", "결과", "model", "route")
INDEX_ALIASES = ("no", "번호", "index", "id", "#")


def read_prompt_label_csv_text(csv_text: str) -> list[dict[str, str | float]]:
    """Read prompt/routing_score CSV text.

    Current format:

    prompt,routing_score
    안녕,8

    Older cheap/mid/premium label files are accepted as a migration aid. Their
    labels are mapped to representative scores: cheap=20, mid=55, premium=85.
    If a prompt contains unquoted commas, the final field is treated as the
    score or legacy label and earlier fields are joined back into the prompt.
    """
    if not csv_text.strip():
        raise ValueError("csv_text_required")

    normalized_text = csv_text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(normalized_text), restkey="__extra_columns__")
    if not reader.fieldnames:
        raise ValueError("CSV/TXT header is required.")

    fieldnames = [str(name or "").strip().lstrip("\ufeff") for name in reader.fieldnames]
    prompt_key = _find_column(fieldnames, PROMPT_ALIASES)
    score_key = _find_column(fieldnames, SCORE_ALIASES)
    legacy_label_key = _find_column(fieldnames, LEGACY_LABEL_ALIASES)
    target_key = score_key or legacy_label_key
    if prompt_key is None or target_key is None:
        prompt_key, target_key = _fallback_columns(fieldnames)

    rows: list[dict[str, str | float]] = []
    for row in reader:
        cleaned = {
            str(key or "").strip().lstrip("\ufeff"): value
            for key, value in row.items()
            if key != "__extra_columns__"
        }
        prompt = str(cleaned.get(prompt_key, "") or "").strip()
        target = str(cleaned.get(target_key, "") or "").strip()
        extra_columns = [str(value or "").strip() for value in row.get("__extra_columns__", [])]

        if extra_columns and _parse_score(extra_columns[-1]) is not None:
            prompt_parts = [prompt, target, *extra_columns[:-1]]
            prompt = ",".join(part for part in prompt_parts if part).strip()
            target = extra_columns[-1]

        score = _parse_score(target)
        if not prompt and target == "":
            continue
        if not prompt or score is None:
            raise ValueError("CSV/TXT must include prompt and routing_score columns. Example: prompt,routing_score")
        rows.append({"prompt": prompt, "routing_score": score})

    if not rows:
        raise ValueError("No trainable/evaluable rows found.")
    return rows


def read_prompt_label_csv_file(csv_path: str | Path) -> list[dict[str, str | float]]:
    return read_prompt_label_csv_text(Path(csv_path).read_text(encoding="utf-8-sig"))


def score_to_model_slot(score: float) -> str:
    if score <= 40:
        return "cheap"
    if score <= 70:
        return "mid"
    return "premium"


def model_slot_to_score(model_slot: str) -> float:
    return LEGACY_LABEL_SCORES.get(str(model_slot).strip().lower(), 0.0)


def _find_column(fieldnames: list[str], aliases: tuple[str, ...]) -> str | None:
    normalized = {_normalize(name): name for name in fieldnames}
    for alias in aliases:
        key = _normalize(alias)
        if key in normalized:
            return normalized[key]
    return None


def _fallback_columns(fieldnames: list[str]) -> tuple[str, str]:
    index_aliases = {_normalize(alias) for alias in INDEX_ALIASES}
    usable = [name for name in fieldnames if _normalize(name) not in index_aliases]
    if len(usable) >= 2:
        return usable[0], usable[1]
    if len(fieldnames) >= 2:
        return fieldnames[0], fieldnames[1]
    raise ValueError("CSV/TXT needs at least two columns.")


def _normalize(value: str) -> str:
    return str(value or "").strip().lower().replace(" ", "").replace("_", "")


def _parse_score(value: str) -> float | None:
    raw = str(value or "").strip()
    legacy_score = LEGACY_LABEL_SCORES.get(raw.lower())
    if legacy_score is not None:
        return legacy_score
    try:
        score = float(raw)
    except ValueError:
        return None
    if not 0.0 <= score <= 100.0:
        return None
    return score
