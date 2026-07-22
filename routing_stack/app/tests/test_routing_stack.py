from __future__ import annotations

from routing_stack.ai.local_ai import LocalAI, ModelConfig
from routing_stack.adapters.contract import Candidate, RouteRequest, RouteResult
from routing_stack.app.router_server import RouterServerApp


class FixedRouter:
    name = "fixed"

    def route(self, request: RouteRequest) -> RouteResult:
        return RouteResult(
            router_name=self.name,
            selected_model_id="cheap",
            action_type="call_model",
            selection_reason="test",
            candidates=[Candidate(model_id="cheap", score=1.0, cost=0.01, feasible=True)],
            diagnostics={"prompt": request.prompt},
        )


def test_local_ai_mock_uses_stable_model_mapping():
    ai = LocalAI(provider="mock", model_config=ModelConfig(cheap="cheap-local", mid="mid-local", premium="top-local"))

    result = ai.run("mid", "hello")

    assert result.provider == "mock"
    assert result.model_slot == "mid"
    assert result.model_name == "mid-local"
    assert result.output == "[mock:mid-local] hello"


def test_route_result_abstain_skips_ai():
    ai = LocalAI(provider="mock")

    result = ai.run(None, "hello")

    assert result.skipped is True
    assert result.model_name is None


def test_router_server_keeps_viewer_router_ai_contract():
    ai = LocalAI(provider="mock", model_config=ModelConfig(cheap="cheap-local"))
    app = RouterServerApp(routers={"fixed": FixedRouter()}, ai=ai, default_router="fixed")

    payload = app.route_and_run({"prompt": "hello", "tier": "fast"})

    assert payload["input"]["prompt"] == "hello"
    assert payload["input"]["router"] == "fixed"
    assert payload["router"]["router_name"] == "fixed"
    assert payload["router"]["model_slot"] == "cheap"
    assert payload["ai"]["model_name"] == "cheap-local"
    assert payload["input"]["input_features"]["simple_directive"] is True
    assert payload["input"]["normalized"]["input_type"] == "text"
    assert payload["input"]["normalized"]["router_features"]["simple_directive"] is True
    assert payload["input"]["routing_context"]["router_context"]["missing_context"] is False


def test_router_server_uses_requested_router():
    ai = LocalAI(provider="mock")
    app = RouterServerApp(routers={"fixed": FixedRouter()}, ai=ai, default_router="fixed")

    payload = app.route_and_run({"router": "fixed", "prompt": "hello", "tier": "fast"})

    assert payload["router"]["router_name"] == "fixed"


def test_router_server_resolves_code_reference_from_conversation():
    ai = LocalAI(provider="mock")
    app = RouterServerApp(routers={"fixed": FixedRouter()}, ai=ai, default_router="fixed")

    payload = app.route_and_run(
        {
            "router": "fixed",
            "prompt": "다음 코드를 분석해줘",
            "conversation": [{"role": "user", "content": "```python\nprint(1)\n```"}],
        }
    )

    context = payload["input"]["routing_context"]["router_context"]
    assert payload["input"]["input_features"]["missing_context"] is True
    assert context["has_resolved_reference"] is True
    assert context["missing_context"] is False


