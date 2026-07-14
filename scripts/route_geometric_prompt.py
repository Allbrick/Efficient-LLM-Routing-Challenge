from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from geometric_router.router import GeometricRouter


def main() -> None:
    parser = argparse.ArgumentParser(description="Route one prompt with the geometric router.")
    parser.add_argument("prompt")
    parser.add_argument("--tier", default="balanced", choices=["fast", "balanced", "premium"])
    parser.add_argument("--artifact", default="artifacts/geometric_router.json")
    parser.add_argument("--task_type", default="")
    parser.add_argument("--difficulty", default="")
    parser.add_argument("--risk_level", default="")
    parser.add_argument("--evaluation_type", default="")
    args = parser.parse_args()

    router = GeometricRouter.load(args.artifact)
    decision = router.route(
        args.prompt,
        budget_tier=args.tier,
        task_type=args.task_type,
        difficulty=args.difficulty,
        risk_level=args.risk_level,
        evaluation_type=args.evaluation_type,
    )
    print(json.dumps(asdict(decision), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
