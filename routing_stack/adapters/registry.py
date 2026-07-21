from __future__ import annotations

from routing_stack.adapters.contract import RouterAdapter
from routing_stack.adapters.geometric_adapter import GeometricRouterAdapter


ROUTER_NAMES = ("geometric", "quality_utility", "orchestrator")


def available_routers() -> list[str]:
    return list(ROUTER_NAMES)


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
    raise ValueError(f"알 수 없는 라우터입니다: {name}")


