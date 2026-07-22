from __future__ import annotations

import csv
import io
from pathlib import Path


LABELS = {"cheap", "mid", "premium"}
PROMPT_ALIASES = ("prompt", "프롬프트", "질문", "입력", "input", "user_prompt")
LABEL_ALIASES = ("정답", "label", "answer", "expected", "예상", "결과", "라우터", "model", "route")
INDEX_ALIASES = ("no", "번호", "index", "id", "#")


def read_prompt_label_csv_text(csv_text: str) -> list[dict[str, str]]:
    """Prompt/정답 CSV 또는 TXT를 관대하게 읽습니다.

    지원 헤더:
    - Prompt,정답
    - 프롬프트,예상
    - question,label
    - 번호,프롬프트,정답

    헤더 이름을 못 찾으면 첫 두 개의 유효 컬럼을 prompt/label로 사용합니다.
    """
    if not csv_text.strip():
        raise ValueError("csv_text_required")
    normalized_text = csv_text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(normalized_text), restkey="__extra_columns__")
    if not reader.fieldnames:
        raise ValueError("CSV/TXT 헤더가 필요합니다.")

    fieldnames = [str(name or "").strip().lstrip("\ufeff") for name in reader.fieldnames]
    prompt_key = _find_column(fieldnames, PROMPT_ALIASES)
    label_key = _find_column(fieldnames, LABEL_ALIASES)
    if prompt_key is None or label_key is None:
        prompt_key, label_key = _fallback_columns(fieldnames)

    rows = []
    for row in reader:
        cleaned = {str(key or "").strip().lstrip("\ufeff"): value for key, value in row.items() if key != "__extra_columns__"}
        prompt = str(cleaned.get(prompt_key, "") or "").strip()
        label = str(cleaned.get(label_key, "") or "").strip().lower()
        extra_columns = [str(value or "").strip() for value in row.get("__extra_columns__", [])]
        if extra_columns and extra_columns[-1].lower() in LABELS:
            prompt_parts = [prompt, str(cleaned.get(label_key, "") or "").strip(), *extra_columns[:-1]]
            prompt = ",".join(part for part in prompt_parts if part).strip()
            label = extra_columns[-1].lower()
        if not prompt and not label:
            continue
        if not prompt or label not in LABELS:
            raise ValueError(
                "CSV/TXT는 프롬프트 컬럼과 정답(cheap/mid/premium) 컬럼이 필요합니다. "
                "예: Prompt,정답 또는 프롬프트,예상"
            )
        rows.append({"prompt": prompt, "label": label})
    if not rows:
        raise ValueError("학습/평가 가능한 row가 없습니다.")
    return rows


def read_prompt_label_csv_file(csv_path: str | Path) -> list[dict[str, str]]:
    return read_prompt_label_csv_text(Path(csv_path).read_text(encoding="utf-8-sig"))


def _find_column(fieldnames: list[str], aliases: tuple[str, ...]) -> str | None:
    normalized = {_normalize(name): name for name in fieldnames}
    for alias in aliases:
        key = _normalize(alias)
        if key in normalized:
            return normalized[key]
    return None


def _fallback_columns(fieldnames: list[str]) -> tuple[str, str]:
    usable = [name for name in fieldnames if _normalize(name) not in {_normalize(alias) for alias in INDEX_ALIASES}]
    if len(usable) >= 2:
        return usable[0], usable[1]
    if len(fieldnames) >= 2:
        return fieldnames[0], fieldnames[1]
    raise ValueError("CSV/TXT는 최소 2개 컬럼이 필요합니다.")


def _normalize(value: str) -> str:
    return str(value or "").strip().lower().replace(" ", "").replace("_", "")
