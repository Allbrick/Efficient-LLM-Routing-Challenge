from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from routing_stack.input.text_features import analyze_text_prompt


SUPPORTED_INPUT_TYPES = ("text",)


@dataclass(frozen=True)
class NormalizedInput:
    input_type: str
    text: str
    router_features: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_input(payload: dict[str, Any]) -> NormalizedInput:
    """viewer 입력을 라우터가 볼 수 있는 정규화 입력으로 변환합니다.

    현재는 text만 지원합니다. 파일, 이미지, PDF가 추가되더라도 라우터는
    원본 파일을 직접 보지 않고 이 함수가 만든 text와 router_features만 받습니다.
    """
    input_type = str(payload.get("input_type", "text")).strip().lower() or "text"
    if input_type != "text":
        raise ValueError(f"unsupported_input_type: {input_type}")

    text = str(payload.get("prompt", "")).strip()
    if not text:
        raise ValueError("prompt_required")

    features = analyze_text_prompt(text).to_dict()
    return NormalizedInput(
        input_type="text",
        text=text,
        router_features=features,
        metadata={
            "normalizer": "text_v1",
            "supported_input_types": list(SUPPORTED_INPUT_TYPES),
        },
    )
