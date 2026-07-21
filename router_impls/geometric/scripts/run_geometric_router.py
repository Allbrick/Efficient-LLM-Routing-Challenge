from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)


def run_script(script_name: str, args: list[str]) -> int:
    command = [sys.executable, str(PROJECT_ROOT / "router_impls" / "geometric" / "scripts" / script_name), *args]
    return subprocess.call(command, cwd=PROJECT_ROOT)


def route_submission(args: argparse.Namespace) -> int:
    from router_impls.geometric.submission import RouterSubmission

    router = RouterSubmission(args.artifact)
    payload = router.route(
        prompt=args.prompt,
        budget_tier=args.tier,
        task_type=args.task_type,
        difficulty=args.difficulty,
        risk_level=args.risk_level,
        evaluation_type=args.evaluation_type,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified entry point for the geometric LLM router.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    train = subparsers.add_parser("train", help="Regenerate router artifact and labels.")
    train.add_argument("--no_tune", action="store_true")
    train.add_argument("--no_synthetic", action="store_true")

    simulate = subparsers.add_parser("simulate", help="Run public-set simulation.")
    simulate.add_argument("--tier", default="fast", choices=["fast", "balanced", "premium"])

    allocate = subparsers.add_parser("allocate", help="Run batch allocation.")
    allocate.add_argument("--tier", default="fast", choices=["fast", "balanced", "premium"])

    viewer = subparsers.add_parser("viewer", help="Serve the viewer.")
    viewer.add_argument("--port", default="4010")

    route = subparsers.add_parser("route", help="Route one prompt through the submission adapter.")
    route.add_argument("prompt")
    route.add_argument("--tier", default="balanced", choices=["fast", "balanced", "premium"])
    route.add_argument("--artifact", default="artifacts/geometric_router.json")
    route.add_argument("--task_type", default="")
    route.add_argument("--difficulty", default="")
    route.add_argument("--risk_level", default="")
    route.add_argument("--evaluation_type", default="")

    args = parser.parse_args()
    if args.command == "train":
        script_args = []
        if args.no_tune:
            script_args.append("--no_tune")
        if args.no_synthetic:
            script_args.append("--no_synthetic")
        return run_script("train_geometric_router.py", script_args)
    if args.command == "simulate":
        return run_script("simulate_geometric_router.py", ["--tier", args.tier])
    if args.command == "allocate":
        return run_script("allocate_geometric_budget.py", ["--tier", args.tier])
    if args.command == "viewer":
        return run_script("serve_geometric_viewer.py", ["--port", args.port])
    if args.command == "route":
        return route_submission(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())


