from __future__ import annotations

import re


_CJK_PATTERN = re.compile(r"[\uac00-\ud7a3\u3040-\u30ff\u4e00-\u9fff]")
_WORD_PATTERN = re.compile(r"[A-Za-z0-9_]+")


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
