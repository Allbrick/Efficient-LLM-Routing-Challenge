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


def test_router_server_evaluates_prompt_label_csv():
    ai = LocalAI(provider="mock")
    app = RouterServerApp(routers={"fixed": FixedRouter()}, ai=ai, default_router="fixed")
    csv_text = "prompt,routing_score\n안녕,8\n"

    payload = app.evaluate_csv({"router": "fixed", "tier": "balanced", "csv_text": csv_text})

    assert payload["row_count"] == 1
    assert payload["correct_count"] == 1
    assert payload["bucket_accuracy"] == 1.0
    assert payload["mae"] == 12.0


def test_router_server_accepts_korean_alias_csv_headers():
    ai = LocalAI(provider="mock")
    app = RouterServerApp(routers={"fixed": FixedRouter()}, ai=ai, default_router="fixed")
    csv_text = "번호,프롬프트,점수\n1,안녕,8\n"

    payload = app.evaluate_csv({"router": "fixed", "tier": "balanced", "csv_text": csv_text})

    assert payload["row_count"] == 1
    assert payload["correct_count"] == 1


def test_router_server_trains_prompt_label_csv(tmp_path):
    ai = LocalAI(provider="mock")
    app = RouterServerApp(routers={"fixed": FixedRouter()}, ai=ai, default_router="fixed")
    output = tmp_path / "prompt_label_router.joblib"
    csv_text = "prompt,routing_score\n안녕,8\nA와 B의 차이를 비교해줘,55\nX를 구현하고 증명해줘,85\n"

    payload = app.train_csv({"csv_text": csv_text, "output_path": str(output)})

    assert output.exists()
    assert payload["row_count"] == 3
    assert payload["bucket_counts"] == {"cheap": 1, "mid": 1, "premium": 1}
    assert "learned_label" in app.routers


def test_router_server_records_feedback(tmp_path):
    ai = LocalAI(provider="mock")
    app = RouterServerApp(routers={"fixed": FixedRouter()}, ai=ai, default_router="fixed")
    output = tmp_path / "online_feedback.csv"

    payload = app.record_feedback(
        {
            "prompt": "라우팅이 틀렸어",
            "budget_tier": "fast",
            "selected_model_id": "cheap",
            "expected_model_id": "mid",
            "selection_reason": "simple_prompt_prior",
            "action_type": "call_model",
            "note": "더 깊은 답 필요",
            "output_path": str(output),
        }
    )

    assert payload["status"] == "appended"
    assert output.exists()
    assert "라우팅이 틀렸어" in output.read_text(encoding="utf-8")


