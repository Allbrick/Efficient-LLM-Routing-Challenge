from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REQUIRED_FILES = (
    "LICENSE",
    "README.md",
    "requirements.txt",
    "docs/REPORT_OUTLINE.md",
    "docs/SUBMISSION.md",
    "docs/SBOM.md",
    "docs/AI_MODEL_USAGE.md",
    "docs/DEMO.md",
    "data/external/dataset_sources.json",
    "data/router_outcomes/README.md",
    "data/router_outcomes/public_outcome_matrix.csv",
    "data/router_outcomes/reviewed_outcome_matrix.csv",
    "router_impls/geometric/submission.py",
    "router_impls/geometric/router.py",
)

REQUIRED_REPORT_ASSETS = (
    "tier_summary.csv",
    "before_after.csv",
    "selection_distribution.csv",
    "error_summary.csv",
    "demo_prompts.csv",
    "fast_allocation_summary.csv",
    "report_assets_summary.json",
    "latency_summary.csv",
    "latency_detail.csv",
    "latency_report.json",
    "policy_preset_comparison.csv",
    "policy_preset_comparison_summary.json",
    "sufficiency_calibration.csv",
    "sufficiency_calibration_summary.csv",
    "sufficiency_calibration_summary.json",
    "ood_calibration.csv",
    "ood_calibration_summary.json",
)

PLACEHOLDER_PATTERNS = {
    "github_url": re.compile(r"GitHub 공개 저장소 URL|https://github\.com/\[계정명\]"),
    "youtube_url": re.compile(r"YouTube URL|시연영상\s*\|\s*YouTube URL"),
    "contest_filename": re.compile(r"접수번호\(팀명\)"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify submission readiness files and known placeholders.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="docs/report_assets/submission_readiness.json")
    parser.add_argument("--strict", action="store_true", help="exit with code 1 when blockers are found")
    args = parser.parse_args()

    report = verify_submission_readiness(Path(args.root))
    output = Path(args.root) / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.strict and report["blockers"]:
        raise SystemExit(1)


def verify_submission_readiness(root: Path) -> dict:
    root = root.resolve()
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    for relative_path in REQUIRED_FILES:
        check_file_exists(root, relative_path, blockers)

    assets_dir = root / "docs" / "report_assets"
    for filename in REQUIRED_REPORT_ASSETS:
        check_file_exists(assets_dir, filename, blockers, base_label="docs/report_assets")

    check_placeholder_text(root, blockers, warnings)
    check_report_asset_rows(root, blockers, warnings)

    return {
        "status": "blocked" if blockers else "ready_with_warnings" if warnings else "ready",
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
        "blockers": blockers,
        "warnings": warnings,
    }


def check_file_exists(root: Path, relative_path: str, blockers: list[dict[str, str]], base_label: str = "") -> None:
    path = root / relative_path
    label = f"{base_label}/{relative_path}" if base_label else relative_path
    if not path.exists():
        blockers.append({"type": "missing_file", "path": label, "message": "required submission file is missing"})
        return
    if path.is_file() and path.stat().st_size == 0:
        blockers.append({"type": "empty_file", "path": label, "message": "required submission file is empty"})


def check_placeholder_text(root: Path, blockers: list[dict[str, str]], warnings: list[dict[str, str]]) -> None:
    files_to_scan = (
        "docs/REPORT_OUTLINE.md",
        "docs/AI_MODEL_USAGE.md",
        "docs/SUBMISSION.md",
    )
    for relative_path in files_to_scan:
        path = root / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for placeholder_type, pattern in PLACEHOLDER_PATTERNS.items():
            if pattern.search(text):
                target = blockers if placeholder_type in {"github_url", "youtube_url"} else warnings
                target.append(
                    {
                        "type": "placeholder",
                        "path": relative_path,
                        "message": f"{placeholder_type} placeholder remains",
                    }
                )


def check_report_asset_rows(root: Path, blockers: list[dict[str, str]], warnings: list[dict[str, str]]) -> None:
    expected_min_rows = {
        "tier_summary.csv": 4,
        "before_after.csv": 4,
        "demo_prompts.csv": 2,
        "latency_summary.csv": 4,
    }
    for filename, min_lines in expected_min_rows.items():
        path = root / "docs" / "report_assets" / filename
        if not path.exists():
            continue
        line_count = sum(1 for _ in path.open("r", encoding="utf-8"))
        if line_count < min_lines:
            blockers.append(
                {
                    "type": "insufficient_rows",
                    "path": f"docs/report_assets/{filename}",
                    "message": f"expected at least {min_lines - 1} data rows",
                }
            )
    report_path = root / "docs" / "report_assets" / "report_assets_summary.json"
    latency_path = root / "docs" / "report_assets" / "latency_report.json"
    for path in (report_path, latency_path):
        if not path.exists():
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            blockers.append({"type": "invalid_json", "path": str(path.relative_to(root)), "message": "invalid JSON"})


if __name__ == "__main__":
    main()
