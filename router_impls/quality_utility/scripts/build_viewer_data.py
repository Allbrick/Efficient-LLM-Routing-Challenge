from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.calibrator import Calibrator
from src.candidate_expander import CandidateExpander
from src.data_models import CostConfig, LambdaParams
from src.feature_extractor import FeatureExtractor
from src.prompt_policy import apply_prompt_prior, estimate_prompt_complexity
from src.quality_predictor import QualityPredictor
from src.utility_engine import CostNormalizer, UtilityEngine


TIERS = ("fast", "balanced", "premium")


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def round_float(value: float, digits: int = 6) -> float:
    return round(float(value), digits)


def build_viewer_data(data_path: Path, artifacts_dir: Path) -> dict:
    data = pd.read_csv(data_path)

    feature_extractor = FeatureExtractor.load(str(artifacts_dir / "feature_pipeline.pkl"))
    model_id_mapping = load_json(artifacts_dir / "model_id_mapping.json")
    expander = CandidateExpander(model_id_mapping)
    predictor = QualityPredictor.load(str(artifacts_dir / "lgbm_model.txt"))
    calibrator = Calibrator.load(str(artifacts_dir / "calibration_params.json"))
    lambda_params = LambdaParams.load(str(artifacts_dir / "lambda_params.json"))
    cost_config = CostConfig.load(str(artifacts_dir / "cost_normalization.json"))
    utility_engine = UtilityEngine(lambda_params, CostNormalizer(cost_config))

    prompts = []
    tier_counts = {tier: {} for tier in TIERS}
    tier_quality = {tier: [] for tier in TIERS}
    tier_cost = {tier: [] for tier in TIERS}

    for prompt_id, group in data.groupby("prompt_id", sort=True):
        first = group.iloc[0]
        model_ids = group["model_id"].tolist()
        prompt_features = feature_extractor.transform([first["prompt"]])
        expanded, expanded_ids = expander.expand(prompt_features, model_ids)
        raw_q = predictor.predict(expanded)
        encoded = np.array([model_id_mapping[mid] for mid in expanded_ids], dtype=np.int32)
        q_cal = calibrator.transform(raw_q, encoded)

        candidates = []
        for idx, (_, row) in enumerate(group.reset_index(drop=True).iterrows()):
            candidates.append(
                {
                    "model_id": row["model_id"],
                    "actual_quality": round_float(row["quality_score"], 4),
                    "cost": round_float(row["cost"], 4),
                    "predicted_quality": round_float(raw_q[idx], 6),
                    "calibrated_quality": round_float(q_cal[idx], 6),
                    "model_output": row["model_output"],
                }
            )

        routing = {}
        complexity = estimate_prompt_complexity(first["prompt"])
        for tier in TIERS:
            q_policy = apply_prompt_prior(q_cal, model_ids, first["prompt"], tier)
            utilities = utility_engine.compute_utilities(q_policy, model_ids, tier)
            selected = utility_engine.select(q_policy, model_ids, tier)
            selected_row = group[group["model_id"] == selected].iloc[0]

            tier_counts[tier][selected] = tier_counts[tier].get(selected, 0) + 1
            tier_quality[tier].append(float(selected_row["quality_score"]))
            tier_cost[tier].append(float(selected_row["cost"]))

            routing[tier] = {
                "selected_model_id": selected,
                "selected_actual_quality": round_float(selected_row["quality_score"], 4),
                "selected_cost": round_float(selected_row["cost"], 4),
                "prompt_complexity": round_float(complexity, 4),
                "utilities": {
                    model_ids[i]: round_float(utilities[i], 6)
                    for i in range(len(model_ids))
                },
                "policy_quality": {
                    model_ids[i]: round_float(q_policy[i], 6)
                    for i in range(len(model_ids))
                },
            }

        prompts.append(
            {
                "prompt_id": prompt_id,
                "prompt": first["prompt"],
                "domain": first.get("domain", ""),
                "task_type": first.get("task_type", ""),
                "benchmark_id": first.get("benchmark_id", ""),
                "candidates": candidates,
                "routing": routing,
            }
        )

    summary = {
        "data_path": str(data_path).replace("\\", "/"),
        "artifacts_dir": str(artifacts_dir).replace("\\", "/"),
        "n_rows": int(len(data)),
        "n_prompts": int(data["prompt_id"].nunique()),
        "models": sorted(data["model_id"].unique().tolist()),
        "lambda_params": {
            "fast": lambda_params.fast,
            "balanced": lambda_params.balanced,
            "premium": lambda_params.premium,
        },
        "tier_summary": {},
    }

    for tier in TIERS:
        summary["tier_summary"][tier] = {
            "selection_counts": tier_counts[tier],
            "mean_selected_quality": round_float(np.mean(tier_quality[tier]), 6),
            "mean_selected_cost": round_float(np.mean(tier_cost[tier]), 6),
        }

    holdout_report = artifacts_dir / "holdout_report.json"
    if holdout_report.exists():
        summary["holdout_report"] = load_json(holdout_report)

    return {"summary": summary, "prompts": prompts}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build static viewer data for router evaluation.")
    parser.add_argument("--data_path", default="../data/public/example_train.csv")
    parser.add_argument("--artifacts_dir", default="artifacts")
    parser.add_argument("--output", default="viewer/router_eval.json")
    args = parser.parse_args()

    payload = build_viewer_data(Path(args.data_path), Path(args.artifacts_dir))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    js_output = output.with_suffix(".js")
    with js_output.open("w", encoding="utf-8") as f:
        f.write("window.ROUTER_EVAL = ")
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write(";\n")
    print(f"Viewer data saved to {output}")
    print(f"Viewer script saved to {js_output}")
    print(f"Prompts: {payload['summary']['n_prompts']}, rows: {payload['summary']['n_rows']}")


if __name__ == "__main__":
    main()
