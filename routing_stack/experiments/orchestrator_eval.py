from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from routing_stack.adapters.contract import RouteRequest, RouterAdapter
from routing_stack.adapters.registry import available_routers, create_router
from routing_stack.context import resolve_context
from routing_stack.input import normalize_input


def evaluate_public(
    dataset_path: str | Path = "data/public/example_train.csv",
    tiers: list[str] | None = None,
    router_names: list[str] | None = None,
    context_fixture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """공개 train 샘플을 이용해 라우터 선택을 근사 평가합니다."""
    tiers = tiers or ["fast", "balanced", "premium"]
    router_names = router_names or available_routers()
    examples = _load_examples(dataset_path)
    routers = {name: create_router(name) for name in router_names}
    stats = {
        router_name: {
            tier: {
                "quality_sum": 0.0,
                "cost_sum": 0.0,
                "count": 0,
                "selection_counts": Counter(),
                "uncertain_count": 0,
                "router_disagreement_count": 0,
            }
            for tier in tiers
        }
        for router_name in routers
    }

    for example in examples:
        payload = {"input_type": "text", "prompt": example["prompt"], **(context_fixture or {})}
        normalized = normalize_input(payload)
        routing_context = resolve_context(payload, normalized)
        for tier in tiers:
            request = RouteRequest(
                prompt=normalized.text,
                tier=tier,
                input_features=normalized.router_features,
                context_features=routing_context.router_context,
                executor_context=routing_context.executor_context,
                call_history=routing_context.session_state.previous_calls,
            )
            for router_name, router in routers.items():
                result = router.route(request)
                selected = result.selected_model_id
                score = example["scores"].get(selected, {"quality": 0.0, "cost": 0.0})
                bucket = stats[router_name][tier]
                bucket["quality_sum"] += score["quality"]
                bucket["cost_sum"] += score["cost"]
                bucket["count"] += 1
                bucket["selection_counts"][selected] += 1
                uncertainty = result.diagnostics.get("uncertainty") or {}
                signals = uncertainty.get("signals") or {}
                if uncertainty.get("uncertain"):
                    bucket["uncertain_count"] += 1
                if signals.get("router_disagreement"):
                    bucket["router_disagreement_count"] += 1

    return {
        "dataset": str(dataset_path),
        "example_count": len(examples),
        "context_fixture_applied": bool(context_fixture),
        "tier_summary": _summarize(stats),
    }


def _load_examples(dataset_path: str | Path) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    with Path(dataset_path).open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            prompt_id = row["prompt_id"]
            item = grouped.setdefault(prompt_id, {"prompt_id": prompt_id, "prompt": row["prompt"], "scores": {}})
            item["scores"][row["model_id"]] = {
                "quality": float(row.get("quality_score") or 0.0),
                "cost": float(row.get("cost") or 0.0),
            }
    return list(grouped.values())


def _summarize(stats: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    payload = {}
    for router_name, by_tier in stats.items():
        payload[router_name] = {}
        for tier, bucket in by_tier.items():
            count = bucket["count"] or 1
            payload[router_name][tier] = {
                "mean_quality": round(bucket["quality_sum"] / count, 6),
                "mean_cost": round(bucket["cost_sum"] / count, 6),
                "selection_counts": dict(bucket["selection_counts"]),
                "uncertain_count": bucket["uncertain_count"],
                "router_disagreement_count": bucket["router_disagreement_count"],
                "count": bucket["count"],
            }
    return payload


def _load_json(path: str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("context fixture는 JSON object여야 합니다.")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="public set 기반 라우터 근사 평가를 실행합니다.")
    parser.add_argument("--dataset", default="data/public/example_train.csv")
    parser.add_argument("--tiers", default="fast,balanced,premium")
    parser.add_argument("--routers", default=",".join(available_routers()))
    parser.add_argument("--context_fixture", default="")
    args = parser.parse_args()
    context_fixture = _load_json(args.context_fixture) if args.context_fixture else None

    payload = evaluate_public(
        dataset_path=args.dataset,
        tiers=[value.strip() for value in args.tiers.split(",") if value.strip()],
        router_names=[value.strip() for value in args.routers.split(",") if value.strip()],
        context_fixture=context_fixture,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
