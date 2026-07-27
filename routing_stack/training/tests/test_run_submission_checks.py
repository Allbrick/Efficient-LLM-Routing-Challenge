from __future__ import annotations

import sys

from scripts.run_submission_checks import build_check_commands, tail


def test_build_check_commands_default_skips_pytest_and_strict():
    commands = build_check_commands(full=False, strict_readiness=False)

    names = [item.name for item in commands]
    readiness = commands[-1].command
    assert names == [
        "train_geometric_router",
        "generate_report_assets",
        "measure_router_latency",
        "verify_submission_readiness",
    ]
    assert readiness[0] == sys.executable
    assert "--strict" not in readiness


def test_build_check_commands_full_adds_pytest_and_strict():
    commands = build_check_commands(full=True, strict_readiness=True)

    assert commands[-1].name == "pytest_related"
    assert "--strict" in commands[-2].command


def test_tail_keeps_last_lines():
    assert tail("a\nb\nc", max_lines=2) == "b\nc"
