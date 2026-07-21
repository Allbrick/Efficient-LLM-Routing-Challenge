from routing_stack.adapters.contract import Candidate, RouteResult
from routing_stack.planning.geometric_signals import extract_geometric_signals


def test_missing_geometric_result_is_unavailable():
    signals = extract_geometric_signals(None)

    assert signals.available is False


def test_extracts_candidate_metrics_and_simple_prior():
    result = RouteResult(
        router_name="geometric",
        selected_model_id="cheap",
        action_type="call_model",
        selection_reason="simple_prompt_prior",
        candidates=[
            Candidate(
                model_id="cheap",
                metrics={
                    "distance": 1.2,
                    "normalized_distance": 0.8,
                    "pass_probability": 0.76,
                    "sufficiency_probability": 0.8,
                    "feasible": True,
                },
            )
        ],
        diagnostics={
            "evidence": {"simple_prompt_prior": 1.0},
            "frontier_hint": {"model_id": "cheap"},
        },
    )

    signals = extract_geometric_signals(result)

    assert signals.available is True
    assert signals.simple_prompt_prior is True
    assert signals.frontier_model_id == "cheap"
    assert signals.model_distance["cheap"] == 1.2
    assert signals.signals["cheap_geometrically_safe"] is True


def test_only_premium_near_and_all_far_signals():
    premium_near = RouteResult(
        router_name="geometric",
        selected_model_id="premium",
        action_type="call_model",
        selection_reason="test",
        candidates=[
            Candidate(model_id="cheap", metrics={"normalized_distance": 2.4, "pass_probability": 0.2, "sufficiency_probability": 0.2}),
            Candidate(model_id="mid", metrics={"normalized_distance": 1.8, "pass_probability": 0.4, "sufficiency_probability": 0.5}),
            Candidate(model_id="premium", metrics={"normalized_distance": 1.0, "pass_probability": 0.9, "sufficiency_probability": 0.9}),
        ],
    )
    all_far = RouteResult(
        router_name="geometric",
        selected_model_id="premium",
        action_type="call_model",
        selection_reason="test",
        candidates=[
            Candidate(model_id="cheap", metrics={"normalized_distance": 3.0, "sufficiency_probability": 0.3}),
            Candidate(model_id="mid", metrics={"normalized_distance": 2.8, "sufficiency_probability": 0.4}),
            Candidate(model_id="premium", metrics={"normalized_distance": 2.6, "sufficiency_probability": 0.9}),
        ],
    )

    assert extract_geometric_signals(premium_near).signals["only_premium_near"] is True
    assert extract_geometric_signals(all_far).signals["all_envelopes_far"] is True
    assert extract_geometric_signals(all_far).signals["high_under_route_risk"] is True
