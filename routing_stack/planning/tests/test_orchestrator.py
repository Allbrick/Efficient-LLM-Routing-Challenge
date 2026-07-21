from routing_stack.adapters.contract import RouteRequest, RouteResult
from routing_stack.planning.orchestrator import orchestrate_route
from routing_stack.planning.types import GeometricSignals, RouterObservation, UncertaintySignal


def obs(name, selected="cheap", quality=None, utility=None):
    return RouterObservation(
        router_name=name,
        selected_model_id=selected,
        selection_reason="test",
        model_quality=quality or {"cheap": 0.8, "mid": 0.7, "premium": 0.6},
        model_utility=utility or {"cheap": 0.8, "mid": 0.7, "premium": 0.6},
        model_cost={"cheap": 0.01, "mid": 0.05, "premium": 0.2},
        raw_result=RouteResult(name, selected, "call_model", "test"),
    )


def uncertainty(**signals):
    return UncertaintySignal(
        uncertain=bool(signals),
        confidence=0.5 if signals else 0.9,
        reason=next(iter(signals), "confident"),
        signals={key: bool(value) for key, value in signals.items()},
        metrics={},
    )


def test_keeps_agreed_cheap_selection():
    result = orchestrate_route(
        RouteRequest(prompt="hello", tier="balanced"),
        [obs("a"), obs("b")],
        uncertainty(),
    )

    assert result.selected_model_id == "cheap"
    assert result.selection_reason == "router_agreement"


def test_fast_simple_directive_selects_cheap():
    request = RouteRequest(prompt="hello", tier="fast", input_features={"simple_directive": True})
    result = orchestrate_route(request, [obs("a", "premium")], uncertainty(router_disagreement=True))

    assert result.selected_model_id == "cheap"
    assert result.selection_reason == "simple_directive"


def test_missing_context_selects_abstain():
    request = RouteRequest(prompt="이 코드를 고쳐줘", tier="balanced", input_features={"missing_context": True})
    result = orchestrate_route(request, [obs("a", "premium")], uncertainty(missing_context=True))

    assert result.selected_model_id == "abstain"
    assert result.action_type == "abstain"


def test_geometric_cheap_safe_blocks_fast_premium():
    request = RouteRequest(prompt="test", tier="fast")
    geo = GeometricSignals(available=True, signals={"cheap_geometrically_safe": True})
    result = orchestrate_route(
        request,
        [obs("a", "premium", quality={"cheap": 0.3, "mid": 0.5, "premium": 0.9})],
        uncertainty(high_premium_gap=True),
        geo,
    )

    assert result.selected_model_id == "cheap"
    assert result.selection_reason == "cheap_geometrically_safe"


def test_premium_tier_uses_only_premium_near():
    request = RouteRequest(prompt="hard", tier="premium")
    geo = GeometricSignals(available=True, signals={"only_premium_near": True})
    result = orchestrate_route(
        request,
        [obs("a", "premium", quality={"cheap": 0.3, "mid": 0.5, "premium": 0.9})],
        uncertainty(high_premium_gap=True),
        geo,
    )

    assert result.selected_model_id == "premium"
    assert result.selection_reason == "only_premium_near"
    assert result.diagnostics["geometric_signals"]["signals"]["only_premium_near"] is True
