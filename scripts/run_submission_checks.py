from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


PYTEST_TARGETS = (
    "routing_stack/app/tests",
    "routing_stack/adapters/tests",
    "routing_stack/input/tests",
    "routing_stack/training/tests",
    "router_impls/geometric/tests",
)


@dataclass(frozen=True)
class CheckCommand:
    name: str
    command: list[str]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run reproducibility checks for contest submission.")
    parser.add_argument("--full", action="store_true", help="also run the full related pytest suite")
    parser.add_argument("--strict-readiness", action="store_true", help="fail when readiness placeholders remain")
    parser.add_argument("--output", default="docs/report_assets/submission_check_run.json")
    args = parser.parse_args()

    commands = build_check_commands(full=args.full, strict_readiness=args.strict_readiness)
    report = run_commands(commands)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["failed"]:
        raise SystemExit(1)


def build_check_commands(full: bool = False, strict_readiness: bool = False) -> list[CheckCommand]:
    readiness_command = [
        sys.executable,
        "scripts/verify_submission_readiness.py",
        "--output",
        "docs/report_assets/submission_readiness.json",
    ]
    if strict_readiness:
        readiness_command.append("--strict")

    commands = [
        CheckCommand(
            "train_geometric_router",
            [
                sys.executable,
                "router_impls/geometric/scripts/train_geometric_router.py",
                "--include_feedback",
                "--outcome_matrix_path",
                "data/router_outcomes/reviewed_outcome_matrix.csv",
                "--policy_report",
                "artifacts/geometric_policy_report.json",
            ],
        ),
        CheckCommand(
            "generate_report_assets",
            [
                sys.executable,
                "scripts/generate_report_assets.py",
                "--outcome_matrix_path",
                "data/router_outcomes/reviewed_outcome_matrix.csv",
                "--output_dir",
                "docs/report_assets",
            ],
        ),
        CheckCommand(
            "generate_outcome_matrix",
            [sys.executable, "scripts/generate_outcome_matrix.py", "--output", "data/router_outcomes/public_outcome_matrix.csv"],
        ),
        CheckCommand(
            "measure_router_latency",
            [sys.executable, "scripts/measure_router_latency.py", "--output_dir", "docs/report_assets", "--repeat", "3"],
        ),
        CheckCommand(
            "generate_geometric_explanations",
            [sys.executable, "scripts/generate_geometric_explanations.py", "--output_dir", "docs/report_assets"],
        ),
        CheckCommand(
            "generate_router_comparison",
            [sys.executable, "scripts/generate_router_comparison.py", "--output_dir", "docs/report_assets"],
        ),
        CheckCommand(
            "generate_policy_preset_comparison",
            [sys.executable, "scripts/generate_policy_preset_comparison.py", "--output_dir", "docs/report_assets"],
        ),
        CheckCommand(
            "generate_sufficiency_calibration",
            [
                sys.executable,
                "scripts/generate_sufficiency_calibration.py",
                "--outcome_matrix_path",
                "data/router_outcomes/reviewed_outcome_matrix.csv",
                "--output_dir",
                "docs/report_assets",
            ],
        ),
        CheckCommand(
            "generate_ood_calibration",
            [
                sys.executable,
                "scripts/generate_ood_calibration.py",
                "--outcome_matrix_path",
                "data/router_outcomes/reviewed_outcome_matrix.csv",
                "--output_dir",
                "docs/report_assets",
            ],
        ),
        CheckCommand("verify_submission_readiness", readiness_command),
    ]
    if full:
        commands.append(CheckCommand("pytest_related", [sys.executable, "-m", "pytest", *PYTEST_TARGETS, "-q"]))
    return commands


def run_commands(commands: list[CheckCommand]) -> dict:
    results = []
    for item in commands:
        started = time.perf_counter()
        completed = subprocess.run(
            item.command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        elapsed = time.perf_counter() - started
        results.append(
            {
                "name": item.name,
                "command": item.command,
                "returncode": completed.returncode,
                "elapsed_seconds": round(elapsed, 3),
                "stdout_tail": tail(completed.stdout),
                "stderr_tail": tail(completed.stderr),
            }
        )
    return {
        "status": "failed" if any(item["returncode"] != 0 for item in results) else "passed",
        "failed": [item for item in results if item["returncode"] != 0],
        "results": results,
    }


def tail(text: str, max_lines: int = 20) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-max_lines:])


if __name__ == "__main__":
    main()
