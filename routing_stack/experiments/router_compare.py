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

from routing_stack.adapters.contract import Candidate, RouteRequest, RouteResult, RouterAdapter
from routing_stack.adapters.registry import available_routers, create_router
from routing_stack.input import normalize_input


RouterFactory = Callable[[str], RouterAdapter]


def compare_routers(
    prompt: str,
    tiers: Iterable[str] = ("fast", "balanced", "premium"),
    router_names: Iterable[str] = ("geometric", "quality_utility"),
    router_factory: RouterFactory = create_router,
) -> dict[str, Any]:
    """같은 프롬프트에 대한 라우터별 모델 품질 예측을 비교합니다."""
    text = str(prompt).strip()
    if not text:
        raise ValueError("prompt_required")

    normalized = normalize_input({"input_type": "text", "prompt": text})
    input_features = normalized.router_features
    routers = {name: router_factory(name) for name in router_names}
    rows = []
    for tier in tiers:
        for router_name, router in routers.items():
            request = RouteRequest(prompt=text, tier=tier, input_features=input_features)
            result = router.route(request)
            rows.append(_result_to_row(tier, result))

    return {
        "prompt": normalized.text,
        "normalized_input": normalized.to_dict(),
        "input_features": input_features,
        "rows": rows,
    }


def _result_to_row(tier: str, result: RouteResult) -> dict[str, Any]:
    return {
        "tier": tier,
        "router": result.router_name,
        "selected_model_id": result.selected_model_id,
        "selection_reason": result.selection_reason,
        "model_quality": {
            candidate.model_id: _candidate_quality(candidate)
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


def _candidate_quality(candidate: Candidate) -> float | None:
    metrics = candidate.metrics or {}
    for key in ("policy_quality", "calibrated_quality", "predicted_quality", "pass_probability"):
        if key in metrics:
            return _as_float(metrics[key])
    return _as_float(candidate.score)


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
    args = parser.parse_args()

    payload = compare_routers(
        prompt=args.prompt,
        tiers=[value.strip() for value in args.tiers.split(",") if value.strip()],
        router_names=[value.strip() for value in args.routers.split(",") if value.strip()],
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
