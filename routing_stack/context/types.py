from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ConversationMessage:
    role: str
    content: str
    created_at: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SessionState:
    summary: str = ""
    current_target: str = ""
    constraints: dict[str, Any] = field(default_factory=dict)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    previous_calls: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ReferenceSignal:
    has_reference_expression: bool
    reference_types: list[str] = field(default_factory=list)
    needs_resolution: bool = False
    matched_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RoutingContext:
    current_prompt: str
    recent_messages: list[ConversationMessage]
    session_state: SessionState
    reference_signal: ReferenceSignal
    router_context: dict[str, Any]
    executor_context: dict[str, Any]
    context_confidence: float

    def to_dict(self) -> dict:
        return {
            "current_prompt": self.current_prompt,
            "recent_messages": [message.to_dict() for message in self.recent_messages],
            "session_state": self.session_state.to_dict(),
            "reference_signal": self.reference_signal.to_dict(),
            "router_context": self.router_context,
            "executor_context": self.executor_context,
            "context_confidence": self.context_confidence,
        }
