from routing_stack.adapters.contract import Candidate, RouteRequest, RouteResult
from routing_stack.adapters.orchestrator_adapter import OrchestratorRouterAdapter


class FakeRouter:
    def __init__(self, name: str, selected: str):
        self.name = name
        self.selected = selected
        self.calls = 0

    def route(self, request: RouteRequest) -> RouteResult:
        self.calls += 1
        return RouteResult(
            router_name=self.name,
            selected_model_id=self.selected,
            action_type="call_model",
            selection_reason="fake",
            candidates=[
                Candidate(
                    model_id="cheap",
                    score=0.8,
                    cost=0.01,
                    feasible=True,
                    metrics={"policy_quality": 0.8},
                ),
                Candidate(
                    model_id="mid",
                    score=0.6,
                    cost=0.05,
                    feasible=True,
                    metrics={"policy_quality": 0.7},
                ),
                Candidate(
                    model_id="premium",
                    score=0.3,
                    cost=0.2,
                    feasible=True,
                    metrics={"policy_quality": 0.75},
                ),
            ],
            diagnostics={},
        )


def test_orchestrator_adapter_calls_base_routers_and_returns_contract():
    geometric = FakeRouter("geometric", "cheap")
    quality = FakeRouter("quality_utility", "cheap")
    adapter = OrchestratorRouterAdapter({"geometric": geometric, "quality_utility": quality})

    result = adapter.route(RouteRequest(prompt="hello", tier="fast", input_features={"simple_directive": True}))

    assert geometric.calls == 1
    assert quality.calls == 1
    assert result.router_name == "orchestrator"
    assert result.selected_model_id == "cheap"
    assert "observations" in result.diagnostics
    assert "uncertainty" in result.diagnostics
