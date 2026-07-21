from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ModelConfig:
    cheap: str = "qwen3:4b-instruct"
    mid: str = "qwen3:8b"
    premium: str = "qwen3:14b"

    def model_for(self, slot: str) -> str:
        if slot not in {"cheap", "mid", "premium"}:
            raise ValueError(f"알 수 없는 모델 슬롯입니다: {slot}")
        return getattr(self, slot)


@dataclass
class AIResult:
    provider: str
    model_slot: str | None
    model_name: str | None
    output: str | None
    skipped: bool = False
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class LocalAI:
    """모든 라우터가 공통으로 사용하는 AI 실행 gateway.

    라우터는 cheap, mid, premium, abstain 같은 논리 슬롯만 선택합니다.
    실제 로컬 모델명과 호출 방식은 이 클래스가 소유합니다.
    """

    def __init__(
        self,
        provider: str = "ollama",
        model_config: ModelConfig | None = None,
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: int = 120,
    ):
        if provider not in {"ollama", "mock"}:
            raise ValueError(f"알 수 없는 AI provider입니다: {provider}")
        self.provider = provider
        self.model_config = model_config or ModelConfig()
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def run(self, model_slot: str | None, prompt: str) -> AIResult:
        if model_slot in {None, "", "abstain"}:
            return AIResult(
                provider=self.provider,
                model_slot=None,
                model_name=None,
                output=None,
                skipped=True,
            )
        model_name = self.model_config.model_for(model_slot)
        if self.provider == "mock":
            return AIResult(
                provider="mock",
                model_slot=model_slot,
                model_name=model_name,
                output=f"[mock:{model_name}] {prompt}",
            )
        return self._run_ollama(model_slot, model_name, prompt)

    def _run_ollama(self, model_slot: str, model_name: str, prompt: str) -> AIResult:
        body = json.dumps(
            {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return AIResult(
                provider="ollama",
                model_slot=model_slot,
                model_name=model_name,
                output=None,
                error=str(exc),
            )
        message = payload.get("message") or {}
        return AIResult(
            provider="ollama",
            model_slot=model_slot,
            model_name=model_name,
            output=message.get("content", ""),
        )

