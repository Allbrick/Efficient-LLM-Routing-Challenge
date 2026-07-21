from routing_stack.adapters.contract import Candidate, RouteRequest, RouteResult
from routing_stack.experiments.router_compare import compare_routers


class FakeRouter:
    def __init__(self, name: str):
        self.name = name

    def route(self, request: RouteRequest) -> RouteResult:
        return RouteResult(
            router_name=self.name,
            selected_model_id="cheap",
            action_type="call_model",
            selection_reason="fake",
            candidates=[
                Candidate(
                    model_id="cheap",
                    score=0.8,
                    cost=0.01,
                    feasible=True,
                    metrics={"predicted_quality": 0.7},
                ),
                Candidate(
                    model_id="mid",
                    score=0.6,
                    cost=0.05,
                    feasible=True,
                    metrics={"policy_quality": 0.75},
                ),
            ],
            diagnostics={"tier": request.tier},
        )


def test_compare_routers_returns_model_quality_table():
    payload = compare_routers(
        "hello",
        tiers=["fast"],
        router_names=["a", "b"],
        router_factory=lambda name: FakeRouter(name),
    )

    assert payload["input_features"]["simple_directive"] is True
    assert [row["router"] for row in payload["rows"]] == ["a", "b"]
    assert payload["rows"][0]["model_quality"] == {"cheap": 0.7, "mid": 0.75}
    assert payload["rows"][0]["model_utility"] == {"cheap": 0.8, "mid": 0.6}
