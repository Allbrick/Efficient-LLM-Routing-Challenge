"""Step 5: Optimize tier-specific lambda values.

Usage:
    python -m training.05_lambda_optimize \
        --oof_path artifacts/oof_predictions.csv \
        --oracle_path artifacts/oracle_analysis.json

Outputs:
    - artifacts/lambda_params.json
    - artifacts/cost_normalization.json
"""

from __future__ import annotations

import argparse
import json
import os

import numpy as np
import pandas as pd

from src.calibrator import Calibrator
from src.data_models import CostConfig, LambdaParams
from src.utility_engine import CostNormalizer, UtilityEngine


DEFAULT_TIER_WEIGHTS = {"fast": 3.0, "balanced": 2.0, "premium": 1.0}

# This is the optimization target's cost sensitivity, not the router lambda.
# It teaches the lambda search what each tier values.
DEFAULT_TIER_COST_WEIGHTS = {
    "fast": 0.45,
    "balanced": 0.14,
    "premium": 0.02,
}


def compute_score(
    data: pd.DataFrame,
    q_cal_col: str,
    lambda_fast: float,
    lambda_balanced: float,
    lambda_premium: float,
    cost_normalizer: CostNormalizer,
    tier_weights: dict[str, float] | None = None,
    tier_cost_weights: dict[str, float] | None = None,
) -> float:
    """Simulate routing score for one lambda combination.

    The router is valuable when it chooses cheaper models whenever their quality
    is sufficient. Therefore the optimizer scores the selected model by:

        actual_quality - tier_cost_weight * normalized_cost

    The selected model is still chosen by the router's predicted utility:

        calibrated_prediction - lambda(tier) * normalized_cost
    """
    if tier_weights is None:
        tier_weights = DEFAULT_TIER_WEIGHTS
    if tier_cost_weights is None:
        tier_cost_weights = DEFAULT_TIER_COST_WEIGHTS

    try:
        lambda_params = LambdaParams(
            fast=lambda_fast,
            balanced=lambda_balanced,
            premium=lambda_premium,
        )
    except ValueError:
        return -1e10

    engine = UtilityEngine(lambda_params, cost_normalizer)

    tier_scores = {}
    for tier in ["fast", "balanced", "premium"]:
        selected_objectives = []
        for _pid, group in data.groupby("prompt_id"):
            model_ids = group["model_id"].tolist()
            q_cal = group[q_cal_col].values
            selected = engine.select(q_cal, model_ids, tier)
            selected_row = group.loc[group["model_id"] == selected].iloc[0]

            actual_q = float(selected_row["quality_score"])
            selected_cost_norm = float(
                cost_normalizer.normalize(
                    [selected],
                    np.array([selected_row["cost"]], dtype=np.float64),
                )[0]
            )
            selected_objectives.append(
                actual_q - tier_cost_weights[tier] * selected_cost_norm
            )

        tier_scores[tier] = float(np.mean(selected_objectives))

    total = sum(tier_weights[tier] * tier_scores[tier] for tier in tier_scores)
    return float(total / sum(tier_weights.values()))


def grid_search(
    data: pd.DataFrame,
    q_cal_col: str,
    cost_normalizer: CostNormalizer,
    lambda_range: tuple[float, float],
    grid_size: int = 20,
) -> tuple[LambdaParams, float]:
    """Find lambda values with monotonic tier constraint.

    Constraint:
        lambda_fast >= lambda_balanced >= lambda_premium >= 0
    """
    candidates = np.linspace(lambda_range[0], lambda_range[1], grid_size)

    best_score = -1e10
    best_params: tuple[float, float, float] | None = None

    total_evals = 0
    for lambda_fast in candidates:
        for lambda_balanced in candidates:
            if lambda_balanced > lambda_fast:
                continue
            for lambda_premium in candidates:
                if lambda_premium > lambda_balanced:
                    continue
                total_evals += 1
                score = compute_score(
                    data,
                    q_cal_col,
                    lambda_fast,
                    lambda_balanced,
                    lambda_premium,
                    cost_normalizer,
                )
                if score > best_score:
                    best_score = score
                    best_params = (lambda_fast, lambda_balanced, lambda_premium)

    if best_params is None:
        raise RuntimeError("No valid lambda combination was evaluated.")

    print(f"  Evaluated {total_evals} combinations")
    lambda_params = LambdaParams(
        fast=best_params[0],
        balanced=best_params[1],
        premium=best_params[2],
    )
    return lambda_params, best_score


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimize router lambda values")
    parser.add_argument("--oof_path", default="artifacts/oof_predictions.csv")
    parser.add_argument("--oracle_path", default="artifacts/oracle_analysis.json")
    parser.add_argument("--calibration_path", default="artifacts/calibration_params.json")
    parser.add_argument("--model_id_mapping", default="artifacts/model_id_mapping.json")
    parser.add_argument("--grid_size", type=int, default=15)
    parser.add_argument("--output", default="artifacts/lambda_params.json")
    args = parser.parse_args()

    data = pd.read_csv(args.oof_path).dropna(subset=["oof_q_hat"])
    with open(args.model_id_mapping, encoding="utf-8") as f:
        mapping = json.load(f)
    with open(args.oracle_path, encoding="utf-8") as f:
        oracle = json.load(f)

    calibrator = Calibrator.load(args.calibration_path)
    model_ids_encoded = data["model_id"].map(mapping).values.astype(np.int32)
    data["q_calibrated"] = calibrator.transform(
        data["oof_q_hat"].values,
        model_ids_encoded,
    )

    cost_map = data.groupby("model_id")["cost"].mean().to_dict()
    cost_config = CostConfig(mode="fixed", cost_map=cost_map)
    cost_normalizer = CostNormalizer(cost_config)

    lambda_range = tuple(oracle["transition_points"]["suggested_lambda_range"])
    print(f"Lambda search range: {lambda_range}")
    print(f"Tier objective cost weights: {DEFAULT_TIER_COST_WEIGHTS}")

    print(f"\nRunning grid search (size={args.grid_size})...")
    best_params, best_score = grid_search(
        data,
        "q_calibrated",
        cost_normalizer,
        lambda_range=lambda_range,
        grid_size=args.grid_size,
    )

    print("\n=== Best Lambda ===")
    print(f"  fast:     {best_params.fast:.4f}")
    print(f"  balanced: {best_params.balanced:.4f}")
    print(f"  premium:  {best_params.premium:.4f}")
    print(f"  Score:    {best_score:.6f}")

    output_dir = os.path.dirname(args.output)
    os.makedirs(output_dir, exist_ok=True)
    best_params.save(args.output)
    cost_config.save(os.path.join(output_dir, "cost_normalization.json"))

    print(f"\nSaved to {args.output}")
