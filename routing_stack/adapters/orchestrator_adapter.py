from __future__ import annotations

from collections.abc import Mapping

from routing_stack.adapters.contract import RouteRequest, RouteResult, RouterAdapter
from routing_stack.adapters.geometric_adapter import GeometricRouterAdapter
from routing_stack.adapters.quality_utility_adapter import QualityUtilityRouterAdapter
from routing_stack.planning.geometric_signals import extract_geometric_signals
from routing_stack.planning.orchestrator import orchestrate_route
from routing_stack.planning.types import observation_from_result
from routing_stack.planning.uncertainty import assess_uncertainty


class OrchestratorRouterAdapter:
    name = "orchestrator"

    def __init__(self, base_routers: Mapping[str, RouterAdapter] | None = None):
        self.base_routers = dict(base_routers or self._default_base_routers())

    def route(self, request: RouteRequest) -> RouteResult:
        base_results = []
        for router in self.base_routers.values():
            base_results.append(router.route(request))

        observations = [observation_from_result(result) for result in base_results]
        geometric_result = next((result for result in base_results if result.router_name == "geometric"), None)
        geometric_signals = extract_geometric_signals(geometric_result)
        uncertainty = assess_uncertainty(
            observations=observations,
            input_features=request.input_features or {},
            tier=request.tier,
            geometric_signals=geometric_signals,
        )
        return orchestrate_route(
            request=request,
            observations=observations,
            uncertainty=uncertainty,
            geometric_signals=geometric_signals,
        )

    def _default_base_routers(self) -> dict[str, RouterAdapter]:
        # registry를 거치면 orchestrator 등록 과정과 순환될 수 있어서 직접 생성합니다.
        return {
            "geometric": GeometricRouterAdapter(),
            "quality_utility": QualityUtilityRouterAdapter(),
        }
