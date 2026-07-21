from routing_stack.adapters.contract import RouteResult
from routing_stack.planning.types import GeometricSignals, RouterObservation
from routing_stack.planning.uncertainty import assess_uncertainty


def obs(name, selected="cheap", quality=None):
    return RouterObservation(
        router_name=name,
        selected_model_id=selected,
        selection_reason="test",
        model_quality=quality or {"cheap": 0.8, "mid": 0.6, "premium": 0.4},
        model_utility=quality or {"cheap": 0.8, "mid": 0.6, "premium": 0.4},
        model_cost={"cheap": 0.01, "mid": 0.05, "premium": 0.2},
        raw_result=RouteResult(name, selected, "call_model", "test"),
    )


def test_agreed_routers_are_confident():
    signal = assess_uncertainty([obs("a"), obs("b")], {"estimated_input_tokens": 10}, "balanced")

    assert signal.uncertain is False
    assert signal.signals["router_disagreement"] is False


def test_disagreement_marks_uncertain():
    signal = assess_uncertainty([obs("a", "cheap"), obs("b", "premium")], {}, "balanced")

    assert signal.uncertain is True
    assert signal.reason == "router_disagreement"


def test_small_margin_and_cost_pressure_signals():
    quality = {"cheap": 0.50, "mid": 0.51, "premium": 0.52}
    signal = assess_uncertainty(
        [obs("a", "mid", quality)],
        {"estimated_input_tokens": 800, "estimated_output_tokens": 950},
        "fast",
    )

    assert signal.signals["small_quality_margin"] is True
    assert signal.signals["high_cost_pressure"] is True


def test_geometric_signals_affect_uncertainty():
    geo_far = GeometricSignals(available=True, signals={"all_envelopes_far": True})
    geo_safe = GeometricSignals(available=True, signals={"cheap_geometrically_safe": True})

    far = assess_uncertainty([obs("a")], {}, "balanced", geo_far)
    safe = assess_uncertainty([obs("a")], {}, "fast", geo_safe)

    assert far.signals["geometric_out_of_distribution"] is True
    assert safe.signals["geometric_cheap_safe"] is True
    assert safe.confidence == 1.0
