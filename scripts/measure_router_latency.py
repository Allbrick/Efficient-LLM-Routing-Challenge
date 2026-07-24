from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from router_impls.geometric.router import GeometricRouter


DEFAULT_TIERS = ("fast", "balanced", "premium")


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure local geometric router decision latency.")
    parser.add_argument("--artifact", default="artifacts/geometric_router.json")
    parser.add_argument("--specs_path", default="data/public/example_eval_specs.csv")
    parser.add_argument("--output_dir", default="docs/report_assets")
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--repeat", type=int, default=3)
    args = parser.parse_args()

    router = GeometricRouter.load(args.artifact)
    specs_df = pd.read_csv(args.specs_path)
    summary = measure_router_latency(
        router=router,
        specs_df=specs_df,
        output_dir=args.output_dir,
        warmup=args.warmup,
        repeat=args.repeat,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def measure_router_latency(
    router: GeometricRouter,
    specs_df: pd.DataFrame,
    output_dir: str | Path = "docs/report_assets",
    tiers: tuple[str, ...] = DEFAULT_TIERS,
    warmup: int = 1,
    repeat: int = 3,
) -> dict:
    if repeat <= 0:
        raise ValueError("repeat must be positive")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    clean_specs = specs_df.fillna("")
    for _ in range(max(warmup, 0)):
        for row in clean_specs.head(min(5, len(clean_specs))).itertuples(index=False):
            router.route(
                str(row.prompt),
                budget_tier="fast",
                task_type=str(getattr(row, "task_type", "")),
                difficulty=str(getattr(row, "difficulty", "")),
                risk_level=str(getattr(row, "risk_level", "")),
                evaluation_type=str(getattr(row, "evaluation_type", "")),
            )

    rows = []
    for row in clean_specs.itertuples(index=False):
        prompt_id = str(getattr(row, "prompt_id", ""))
        for tier in tiers:
            timings_ms = []
            last_decision = None
            for _ in range(repeat):
                started = time.perf_counter()
                last_decision = router.route(
                    str(row.prompt),
                    budget_tier=tier,
                    task_type=str(getattr(row, "task_type", "")),
                    difficulty=str(getattr(row, "difficulty", "")),
                    risk_level=str(getattr(row, "risk_level", "")),
                    evaluation_type=str(getattr(row, "evaluation_type", "")),
                )
                timings_ms.append((time.perf_counter() - started) * 1000.0)
            rows.append(
                {
                    "prompt_id": prompt_id,
                    "budget_tier": tier,
                    "selected_model_id": last_decision.selected_model_id if last_decision else "",
                    "selection_reason": last_decision.selection_reason if last_decision else "",
                    "latency_ms_mean": statistics.fmean(timings_ms),
                    "latency_ms_min": min(timings_ms),
                    "latency_ms_max": max(timings_ms),
                    "repeat": repeat,
                }
            )

    detail_df = pd.DataFrame(rows)
    summary_df = build_latency_summary(detail_df)
    detail_df.to_csv(output / "latency_detail.csv", index=False, encoding="utf-8")
    summary_df.to_csv(output / "latency_summary.csv", index=False, encoding="utf-8")
    summary = {
        "output_dir": str(output),
        "n_prompts": int(clean_specs["prompt_id"].nunique()) if "prompt_id" in clean_specs else int(len(clean_specs)),
        "repeat": repeat,
        "summary": summary_df.to_dict(orient="records"),
        "files": ["latency_summary.csv", "latency_detail.csv"],
    }
    (output / "latency_report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def build_latency_summary(detail_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for tier, group in detail_df.groupby("budget_tier", sort=False):
        values = group["latency_ms_mean"].astype(float).sort_values().tolist()
        rows.append(
            {
                "budget_tier": tier,
                "count": int(len(values)),
                "latency_ms_mean": statistics.fmean(values) if values else 0.0,
                "latency_ms_p50": percentile(values, 0.50),
                "latency_ms_p95": percentile(values, 0.95),
                "latency_ms_max": max(values) if values else 0.0,
            }
        )
    return pd.DataFrame(rows)


def percentile(sorted_values: list[float], ratio: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    position = (len(sorted_values) - 1) * ratio
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return float(sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight)


if __name__ == "__main__":
    main()
