"""Step 4: Calibration 학습 및 평가.

사용법:
    python -m training.04_calibration --oof_path artifacts/oof_predictions.csv

산출물:
    - artifacts/calibration_params.json
    - calibration 평가 지표 출력
"""

import argparse
import os

import numpy as np
import pandas as pd

from src.calibrator import Calibrator


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calibration 학습")
    parser.add_argument("--oof_path", default="artifacts/oof_predictions.csv")
    parser.add_argument("--method", default="bias", choices=["bias", "linear"])
    parser.add_argument("--model_id_mapping", default="artifacts/model_id_mapping.json")
    parser.add_argument("--output", default="artifacts/calibration_params.json")
    args = parser.parse_args()

    import json
    with open(args.model_id_mapping) as f:
        mapping = json.load(f)

    data = pd.read_csv(args.oof_path)
    data = data.dropna(subset=["oof_q_hat"])

    model_ids_encoded = data["model_id"].map(mapping).values.astype(np.int32)
    q_hat = data["oof_q_hat"].values
    q_true = data["quality_score"].values
    prompt_ids = data["prompt_id"].values

    # Fit
    cal = Calibrator(method=args.method)
    cal.fit(q_hat, q_true, model_ids_encoded)

    # Evaluate
    metrics = cal.evaluate(q_hat, q_true, model_ids_encoded, prompt_ids)

    print("\n=== Calibration Report ===")
    print(f"  Method: {args.method}")
    print(f"  Overall MAE: {metrics['overall_mae']:.6f}")
    print(f"  Pairwise Ranking Accuracy: {metrics['pairwise_ranking_accuracy']:.4f}")
    print(f"  Best-Model Selection Accuracy: {metrics['best_model_selection_accuracy']:.4f}")

    # Per-model residual
    q_cal = cal.transform(q_hat, model_ids_encoded)
    reverse_mapping = {v: k for k, v in mapping.items()}
    for mid in sorted(cal._params.keys()):
        mask = model_ids_encoded == mid
        residual = np.mean(q_true[mask] - q_cal[mask])
        mae = np.mean(np.abs(q_true[mask] - q_cal[mask]))
        print(f"  {reverse_mapping[mid]}: MAE={mae:.6f}, mean_residual={residual:.6f}, params={cal._params[mid]}")

    # Save
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    cal.save(args.output)
    print(f"\nSaved to {args.output}")
