from pathlib import Path

from routing_stack.adapters.contract import RouteRequest
from routing_stack.adapters.learned_label_adapter import LearnedLabelRouterAdapter
from routing_stack.training.prompt_label_model import PromptLabelRouterModel


def test_learned_label_adapter_returns_route_result(tmp_path: Path):
    artifact = tmp_path / "router.joblib"
    PromptLabelRouterModel().fit(
        ["안녕", "A와 B의 차이를 비교해줘", "X를 구현하고 증명해줘"],
        ["cheap", "mid", "premium"],
    ).save(artifact)
    adapter = LearnedLabelRouterAdapter(artifact)

    result = adapter.route(RouteRequest(prompt="안녕", tier="balanced"))

    assert result.router_name == "learned_label"
    assert result.selected_model_id in {"cheap", "mid", "premium"}
    assert result.diagnostics["probabilities"]
