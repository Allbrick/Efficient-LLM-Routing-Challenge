from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from routing_stack.training.external_dataset import (
    filter_routing_rows,
    load_dataset_sources,
    read_routing_csv,
    validate_source_manifest,
    write_routing_csv,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Filter external routing dataset rows and preserve source/license fields.")
    parser.add_argument("--input", required=True, help="Input CSV with external routing rows.")
    parser.add_argument("--output", default="data/external/routing_prompts.csv")
    parser.add_argument("--manifest", default="data/external/dataset_sources.json")
    parser.add_argument("--report", default="data/external/filter_report.json")
    parser.add_argument("--max_prompt_chars", type=int, default=1200)
    args = parser.parse_args()

    manifest_errors = validate_source_manifest(args.manifest)
    if manifest_errors:
        raise SystemExit("Invalid source manifest:\n" + "\n".join(manifest_errors))

    sources = load_dataset_sources(args.manifest)
    rows = read_routing_csv(args.input)
    filtered_rows, report = filter_routing_rows(rows, sources, max_prompt_chars=args.max_prompt_chars)
    write_routing_csv(args.output, filtered_rows)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
