from __future__ import annotations

import re
from dataclasses import asdict, dataclass


_CJK_PATTERN = re.compile(r"[\uac00-\ud7a3\u3040-\u30ff\u4e00-\u9fff]")
_WORD_PATTERN = re.compile(r"[A-Za-z0-9_]+")
_CODE_PATTERN = re.compile(
    r"(```|def\s+\w+|class\s+\w+|function\s+\w+|const\s+\w+|let\s+\w+|"
    r"import\s+\w+|SELECT\s+|CREATE\s+TABLE|[{};]|\=\>)",
    re.IGNORECASE,
)
_JSON_OR_TABLE_PATTERN = re.compile(
    r"(\{|\}|\[|\]|\"[^\"]+\"\s*:|^\s*\|.+\|\s*$|,.*,\n|csv|json|table|표)",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class TokenEstimate:
    estimated_input_tokens: int
    estimated_output_tokens: int
    token_per_char: float
    code_token_pressure: float
    json_or_table_pressure: float

    def to_dict(self) -> dict:
        return asdict(self)


def estimate_text_tokens(text: str) -> int:
    """로컬에서 재현 가능한 대략적인 입력 토큰 수를 계산합니다.

    실제 모델 토크나이저 대신 라우팅 특징으로 쓰기 위한 추정치입니다.
    외부 모델이나 네트워크를 호출하지 않습니다.
    """
    value = str(text)
    if not value.strip():
        return 0

    cjk_chars = len(_CJK_PATTERN.findall(value))
    word_tokens = len(_WORD_PATTERN.findall(value))
    punctuation_tokens = sum(1 for char in value if not char.isalnum() and not char.isspace())
    whitespace_adjustment = max(0, len(value.split()) - word_tokens)

    return max(1, int(round(cjk_chars * 0.7 + word_tokens * 1.3 + punctuation_tokens * 0.5 + whitespace_adjustment)))


def estimate_prompt_tokens(text: str) -> TokenEstimate:
    """라우터용 비용/복잡도 토큰 feature를 추정합니다.

    LLM 토크나이저를 직접 쓰지 않고, 로컬 규칙만으로 Fast tier에서 중요한
    입력 비용과 출력 비용 압력을 대략적으로 계산합니다.
    """
    value = str(text).strip()
    if not value:
        return TokenEstimate(
            estimated_input_tokens=0,
            estimated_output_tokens=0,
            token_per_char=0.0,
            code_token_pressure=0.0,
            json_or_table_pressure=0.0,
        )

    input_tokens = estimate_text_tokens(value)
    code_pressure = _code_token_pressure(value)
    json_or_table_pressure = _json_or_table_pressure(value)
    output_tokens = _estimate_output_tokens(value, input_tokens, code_pressure, json_or_table_pressure)

    return TokenEstimate(
        estimated_input_tokens=input_tokens,
        estimated_output_tokens=output_tokens,
        token_per_char=round(input_tokens / max(len(value), 1), 6),
        code_token_pressure=round(code_pressure, 6),
        json_or_table_pressure=round(json_or_table_pressure, 6),
    )


def _estimate_output_tokens(
    text: str,
    input_tokens: int,
    code_pressure: float,
    json_or_table_pressure: float,
) -> int:
    lowered = text.lower()
    asks_short_answer = any(term in lowered for term in ("값만", "숫자로", "한 단어", "only", "one word"))
    asks_long_answer = any(term in lowered for term in ("설명", "분석", "작성", "설계", "정리", "explain", "analyze", "write", "design"))

    if asks_short_answer and input_tokens < 80:
        base = 12
    elif asks_long_answer:
        base = max(96, int(input_tokens * 0.75))
    else:
        base = max(32, int(input_tokens * 0.45))

    pressure_multiplier = 1.0 + 0.8 * code_pressure + 0.45 * json_or_table_pressure
    return max(1, int(round(base * pressure_multiplier)))


def _code_token_pressure(text: str) -> float:
    delimiter_count = sum(text.count(token) for token in ("```", "{", "}", ";", "=>", "()", "[]"))
    line_count = text.count("\n") + 1
    pattern_bonus = 2 if _CODE_PATTERN.search(text) else 0
    return min((delimiter_count + pattern_bonus + max(0, line_count - 4) * 0.2) / 10.0, 1.0)


def _json_or_table_pressure(text: str) -> float:
    structural_chars = sum(text.count(token) for token in ("{", "}", "[", "]", ":", "|", ","))
    pattern_bonus = 2 if _JSON_OR_TABLE_PATTERN.search(text) else 0
    return min((structural_chars + pattern_bonus) / 18.0, 1.0)
