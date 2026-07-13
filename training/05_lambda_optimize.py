"""Step 5: Lambda 최적화.

사용법:
    python -m training.05_lambda_optimize \
        --oof_path artifacts/oof_predictions.csv \
        --oracle_path artifacts/oracle_analysis.json

산출물:
    - artifacts/lambda_params.json
"""

import argparse
import json
import os

import numpy as np
import pandas as pd

from src.calibrator import Calibrator
from src.data_models import CostConfig, LambdaParams
from src.utility_engine import CostNormalizer, UtilityEngine


def compute_score(
    data: pd.DataFrame,
    q_cal_col: str,
    model_id_mapping: dict,
    lambda_fast: float,
    lambda_balanced: float,
    lambda_premium: float,
    cost_normalizer: CostNormalizer,
    tier_weights: dict | None = None,
) -> float:
    """주어진 lambda 조합으로 대회 메트릭을 시뮬레이션한다.

    각 (prompt_id)에 대해 3개 tier 각각에서 모델을 선택하고,
    선택된 모델의 실제 quality_score의 가중 평균을 계산한다.
    """
    if tier_weights is None:
        tier_weights = {"fast": 3.0, "balanced": 2.0, "premium": 1.0}

    try:
        lp = LambdaParams(fast=lambda_fast, balanced=lambda_balanced, premium=lambda_premium)
    except ValueError:
        return -1e10  # 단조 조건 위반

    engine = UtilityEngine(lp, cost_normalizer)

    tier_scores = {}
    for tier in ["fast", "balanced", "premium"]:
        selected_qualities = []
        for pid, group in data.groupby("prompt_id"):
            model_ids = group["model_id"].tolist()
            q_cal = group[q_cal_col].values
            selected = engine.select(q_cal, model_ids, tier)
            actual_q = group.loc[group["model_id"] == selected, "quality_score"].values[0]
            selected_qualities.append(actual_q)
        tier_scores[tier] = np.mean(selected_qualities)

    total = sum(tier_weights[t] * tier_scores[t] for t in tier_scores)
    total /= sum(tier_weights.values())
    return total


def grid_search(
    data: pd.DataFrame,
    q_cal_col: str,
    model_id_mapping: dict,
    cost_normalizer: CostNormalizer,
    lambda_range: tuple[float, float],
    grid_size: int = 20,
) -> tuple[LambdaParams, float]:
    """Grid Search로 최적 lambda 조합을 찾는다.

    단조 조건: lambda_fast >= lambda_balanced >= lambda_premium >= 0
    """
    candidates = np.linspace(lambda_range[0], lambda_range[1], grid_size)

    best_score = -1e10
    best_params = None

    total_evals = 0
    for lf in candidates:
        for lb in candidates:
            if lb > lf:
                continue
            for lp_val in candidates:
                if lp_val > lb:
                    continue
                total_evals += 1
                score = compute_score(
                    data, q_cal_col, model_id_mapping,
                    lf, lb, lp_val, cost_normalizer,
                )
                if score > best_score:
                    best_score = score
                    best_params = (lf, lb, lp_val)

    print(f"  Evaluated {total_evals} combinations")
    lp = LambdaParams(fast=best_params[0], balanced=best_params[1], premium=best_params[2])
    return lp, best_score


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lambda 최적화")
    parser.add_argument("--oof_path", default="artifacts/oof_predictions.csv")
    parser.add_argument("--oracle_path", default="artifacts/oracle_analysis.json")
    parser.add_argument("--calibration_path", default="artifacts/calibration_params.json")
    parser.add_argument("--model_id_mapping", default="artifacts/model_id_mapping.json")
    parser.add_argument("--grid_size", type=int, default=15)
    parser.add_argument("--output", default="artifacts/lambda_params.json")
    args = parser.parse_args()

    # Load data
    data = pd.read_csv(args.oof_path).dropna(subset=["oof_q_hat"])
    with open(args.model_id_mapping) as f:
        mapping = json.load(f)
    with open(args.oracle_path) as f:
        oracle = json.load(f)

    # Apply calibration
    cal = Calibrator.load(args.calibration_path)
    model_ids_encoded = data["model_id"].map(mapping).values.astype(np.int32)
    q_cal = cal.transform(data["oof_q_hat"].values, model_ids_encoded)
    data["q_calibrated"] = q_cal

    # Cost normalization
    cost_map = data.groupby("model_id")["cost"].mean().to_dict()
    cost_config = CostConfig(mode="fixed", cost_map=cost_map)
    cost_normalizer = CostNormalizer(cost_config)

    # Lambda range from Oracle
    lam_range = oracle["transition_points"]["suggested_lambda_range"]
    print(f"Lambda search range: {lam_range}")

    # Grid search
    print(f"\nRunning grid search (size={args.grid_size})...")
    best_params, best_score = grid_search(
        data, "q_calibrated", mapping, cost_normalizer,
        lambda_range=tuple(lam_range),
        grid_size=args.grid_size,
    )

    print(f"\n=== Best Lambda ===")
    print(f"  fast:     {best_params.fast:.4f}")
    print(f"  balanced: {best_params.balanced:.4f}")
    print(f"  premium:  {best_params.premium:.4f}")
    print(f"  Score:    {best_score:.6f}")

    # Save
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    best_params.save(args.output)

    # Cost normalization도 저장
    cost_config.save(os.path.join(os.path.dirname(args.output), "cost_normalization.json"))
    print(f"\nSaved to {args.output}")
