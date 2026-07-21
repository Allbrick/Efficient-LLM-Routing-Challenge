from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from routing_stack.adapters.contract import RouteRequest, RouteResult, RouterAdapter
from routing_stack.adapters.registry import available_routers, create_router
from routing_stack.input import normalize_input
from routing_stack.planning.geometric_signals import extract_geometric_signals
from routing_stack.planning.orchestrator import orchestrate_route
from routing_stack.planning.types import candidate_quality, observation_from_result
from routing_stack.planning.uncertainty import assess_uncertainty


RouterFactory = Callable[[str], RouterAdapter]


def compare_routers(
    prompt: str,
    tiers: Iterable[str] = ("fast", "balanced", "premium"),
    router_names: Iterable[str] = ("geometric", "quality_utility"),
    router_factory: RouterFactory = create_router,
    include_orchestrator: bool = False,
) -> dict[str, Any]:
    """같은 프롬프트에 대한 라우터별 모델 품질 예측을 비교합니다."""
    text = str(prompt).strip()
    if not text:
        raise ValueError("prompt_required")

    normalized = normalize_input({"input_type": "text", "prompt": text})
    input_features = normalized.router_features
    base_router_names = [name for name in router_names if name != "orchestrator"]
    routers = {name: router_factory(name) for name in base_router_names}
    rows = []
    planning = []
    for tier in tiers:
        tier_results: list[RouteResult] = []
        for router_name, router in routers.items():
            request = RouteRequest(prompt=text, tier=tier, input_features=input_features)
            result = router.route(request)
            tier_results.append(result)
            rows.append(_result_to_row(tier, result))
        if include_orchestrator and tier_results:
            observations = [observation_from_result(result) for result in tier_results]
            geometric_result = next((result for result in tier_results if result.router_name == "geometric"), None)
            geometric_signals = extract_geometric_signals(geometric_result)
            uncertainty = assess_uncertainty(observations, input_features, tier, geometric_signals)
            orchestrator_decision = orchestrate_route(
                RouteRequest(prompt=text, tier=tier, input_features=input_features),
                observations,
                uncertainty,
                geometric_signals,
            )
            rows.append(_result_to_row(tier, orchestrator_decision))
            planning.append(
                {
                    "tier": tier,
                    "uncertainty": uncertainty.to_dict(),
                    "geometric_signals": geometric_signals.to_dict(),
                    "orchestrator_decision": orchestrator_decision.to_dict(),
                }
            )

    return {
        "prompt": normalized.text,
        "normalized_input": normalized.to_dict(),
        "input_features": input_features,
        "rows": rows,
        "planning": planning,
    }


def _result_to_row(tier: str, result: RouteResult) -> dict[str, Any]:
    return {
        "tier": tier,
        "router": result.router_name,
        "selected_model_id": result.selected_model_id,
        "selection_reason": result.selection_reason,
        "model_quality": {
            candidate.model_id: candidate_quality(candidate)
            for candidate in result.candidates
            if candidate.model_id != "abstain"
        },
        "model_utility": {
            candidate.model_id: candidate.score
            for candidate in result.candidates
            if candidate.model_id != "abstain"
        },
        "model_cost": {
            candidate.model_id: candidate.cost
            for candidate in result.candidates
            if candidate.model_id != "abstain"
        },
        "diagnostics": result.diagnostics,
    }


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="라우터별 model quality 예측을 비교합니다.")
    parser.add_argument("prompt")
    parser.add_argument("--tiers", default="fast,balanced,premium")
    parser.add_argument("--routers", default=",".join(available_routers()))
    parser.add_argument("--include_orchestrator", action="store_true")
    args = parser.parse_args()

    payload = compare_routers(
        prompt=args.prompt,
        tiers=[value.strip() for value in args.tiers.split(",") if value.strip()],
        router_names=[value.strip() for value in args.routers.split(",") if value.strip()],
        include_orchestrator=args.include_orchestrator,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
