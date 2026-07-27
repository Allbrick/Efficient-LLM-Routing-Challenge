from __future__ import annotations

import json
from pathlib import Path

from scripts.verify_submission_readiness import verify_submission_readiness


def write(path: Path, text: str = "ok") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def populate_required_files(root: Path) -> None:
    for relative in (
        "LICENSE",
        "README.md",
        "requirements.txt",
        "docs/REPORT_OUTLINE.md",
        "docs/SUBMISSION.md",
        "docs/SBOM.md",
        "docs/AI_MODEL_USAGE.md",
        "docs/DEMO_SCRIPT.md",
        "data/external/dataset_sources.json",
        "router_impls/geometric/submission.py",
        "router_impls/geometric/router.py",
    ):
        write(root / relative)
    for filename in (
        "selection_distribution.csv",
        "error_summary.csv",
        "fast_allocation_summary.csv",
        "latency_detail.csv",
    ):
        write(root / "docs" / "report_assets" / filename, "header\nrow\n")
    write(root / "docs" / "report_assets" / "tier_summary.csv", "h\n1\n2\n3\n")
    write(root / "docs" / "report_assets" / "before_after.csv", "h\n1\n2\n3\n")
    write(root / "docs" / "report_assets" / "demo_prompts.csv", "h\n1\n")
    write(root / "docs" / "report_assets" / "latency_summary.csv", "h\n1\n2\n3\n")
    write(root / "docs" / "report_assets" / "report_assets_summary.json", json.dumps({"ok": True}))
    write(root / "docs" / "report_assets" / "latency_report.json", json.dumps({"ok": True}))


def test_verify_submission_readiness_detects_required_url_placeholders(tmp_path):
    populate_required_files(tmp_path)
    write(tmp_path / "docs" / "REPORT_OUTLINE.md", "GitHub 공개 저장소 URL로 교체\nYouTube URL로 교체")

    report = verify_submission_readiness(tmp_path)

    assert report["status"] == "blocked"
    assert {item["message"] for item in report["blockers"]} >= {
        "github_url placeholder remains",
        "youtube_url placeholder remains",
    }


def test_verify_submission_readiness_passes_when_files_and_urls_are_ready(tmp_path):
    populate_required_files(tmp_path)
    write(tmp_path / "docs" / "REPORT_OUTLINE.md", "https://github.com/user/repo\nhttps://youtube.com/watch?v=abc")
    write(tmp_path / "docs" / "AI_MODEL_USAGE.md", "https://github.com/user/repo")
    write(tmp_path / "docs" / "SUBMISSION.md", "ready")

    report = verify_submission_readiness(tmp_path)

    assert report["status"] == "ready"
    assert report["blockers"] == []
