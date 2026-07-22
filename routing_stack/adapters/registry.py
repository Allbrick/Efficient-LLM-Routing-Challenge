from __future__ import annotations

from pathlib import Path

from routing_stack.adapters.contract import RouterAdapter
from routing_stack.adapters.geometric_adapter import GeometricRouterAdapter


ROUTER_NAMES = ("geometric", "quality_utility", "orchestrator")
LEARNED_LABEL_ARTIFACT = Path("artifacts/prompt_label_router.joblib")


def available_routers() -> list[str]:
    names = list(ROUTER_NAMES)
    if LEARNED_LABEL_ARTIFACT.exists():
        names.append("learned_label")
    return names


def create_router(name: str, artifact: str | None = None) -> RouterAdapter:
    normalized = name.strip().lower().replace("-", "_")
    if normalized == "geometric":
        return GeometricRouterAdapter(artifact or "artifacts/geometric_router.json")
    if normalized in {"quality_utility", "quality"}:
        from routing_stack.adapters.quality_utility_adapter import QualityUtilityRouterAdapter

        return QualityUtilityRouterAdapter(artifact or "router_impls/quality_utility/artifacts")
    if normalized == "orchestrator":
        from routing_stack.adapters.orchestrator_adapter import OrchestratorRouterAdapter

        return OrchestratorRouterAdapter()
    if normalized in {"learned_label", "learned"}:
        from routing_stack.adapters.learned_label_adapter import LearnedLabelRouterAdapter

        return LearnedLabelRouterAdapter(artifact or LEARNED_LABEL_ARTIFACT)
    raise ValueError(f"알 수 없는 라우터입니다: {name}")
