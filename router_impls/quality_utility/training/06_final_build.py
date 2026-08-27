"""Step 6: 최종 모델 빌드 + Holdout 평가.

사용법:
    python -m training.06_final_build --data_path data/public/train.csv

산출물:
    - artifacts/feature_pipeline.pkl
    - artifacts/lgbm_model.txt
    - holdout 평가 결과
"""

import argparse
import json
import os

import numpy as np
import pandas as pd
from importlib import import_module

from src.feature_extractor import FeatureExtractor
from src.quality_predictor import QualityPredictor
from src.calibrator import Calibrator
from src.data_models import CostConfig, LambdaParams
from src.utility_engine import CostNormalizer, UtilityEngine

create_dev_holdout_split = import_module("training.03_train_oof").create_dev_holdout_split


def build_final(
    dev_data: pd.DataFrame,
    model_id_mapping: dict,
    best_iteration: int,
    tfidf_max_features: int = 5000,
    svd_n_components: int = 50,
    lgbm_params: dict | None = None,
    output_dir: str = "artifacts",
) -> None:
    """전체 Development 데이터로 최종 모델을 빌드하고 저장한다."""
    os.makedirs(output_dir, exist_ok=True)

    # 1. Feature Pipeline (전체 dev)
    all_prompts = dev_data.drop_duplicates("prompt_id")["prompt"].tolist()
    extractor = FeatureExtractor(
        tfidf_max_features=tfidf_max_features,
        svd_n_components=svd_n_components,
    )
    extractor.fit(all_prompts)
    extractor.save(os.path.join(output_dir, "feature_pipeline.pkl"))

    # 2. Build features
    unique_df = dev_data.drop_duplicates("prompt_id")
    prompt_feats = extractor.transform(unique_df["prompt"].tolist())
    pid_to_idx = {pid: i for i, pid in enumerate(unique_df["prompt_id"])}

    rows = []
    for _, row in dev_data.iterrows():
        p_idx = pid_to_idx[row["prompt_id"]]
        mid_encoded = model_id_mapping[row["model_id"]]
        feat = np.append(prompt_feats[p_idx], mid_encoded)
        rows.append(feat)

    X = np.array(rows, dtype=np.float32)
    y = dev_data["quality_score"].values.astype(np.float32)

    # 3. LightGBM final train
    cat_col = [X.shape[1] - 1]
    predictor = QualityPredictor(lgbm_params)
    predictor.train_final(X, y, categorical_feature=cat_col, num_boost_round=best_iteration)
    predictor.save(os.path.join(output_dir, "lgbm_model.txt"))

    print(f"Final model saved to {output_dir}/")
    print(f"  Feature dim: {X.shape[1]}")
    print(f"  Training samples: {X.shape[0]}")
    print(f"  Boost rounds: {best_iteration}")


def evaluate_holdout(
    holdout_data: pd.DataFrame,
    model_id_mapping: dict,
    artifacts_dir: str = "artifacts",
) -> dict:
    """Holdout 데이터로 최종 성능을 평가한다."""
    extractor = FeatureExtractor.load(os.path.join(artifacts_dir, "feature_pipeline.pkl"))
    predictor = QualityPredictor.load(os.path.join(artifacts_dir, "lgbm_model.txt"))
    cal = Calibrator.load(os.path.join(artifacts_dir, "calibration_params.json"))
    lp = LambdaParams.load(os.path.join(artifacts_dir, "lambda_params.json"))
    cost_config = CostConfig.load(os.path.join(artifacts_dir, "cost_normalization.json"))

    cost_norm = CostNormalizer(cost_config)
    engine = UtilityEngine(lp, cost_norm)

    # Build features
    unique_df = holdout_data.drop_duplicates("prompt_id")
    prompt_feats = extractor.transform(unique_df["prompt"].tolist())
    pid_to_idx = {pid: i for i, pid in enumerate(unique_df["prompt_id"])}

    rows = []
    for _, row in holdout_data.iterrows():
        p_idx = pid_to_idx[row["prompt_id"]]
        mid_encoded = model_id_mapping[row["model_id"]]
        feat = np.append(prompt_feats[p_idx], mid_encoded)
        rows.append(feat)

    X = np.array(rows, dtype=np.float32)
    raw_q = predictor.predict(X)

    model_ids_encoded = holdout_data["model_id"].map(model_id_mapping).values.astype(np.int32)
    q_cal = cal.transform(raw_q, model_ids_encoded)

    # MAE
    mae = float(np.mean(np.abs(holdout_data["quality_score"].values - q_cal)))

    # Routing simulation
    tier_weights = {"fast": 3.0, "balanced": 2.0, "premium": 1.0}
    tier_scores = {}
    holdout_data = holdout_data.copy()
    holdout_data["q_cal"] = q_cal

    for tier in ["fast", "balanced", "premium"]:
        selected_qualities = []
        for pid, group in holdout_data.groupby("prompt_id"):
            model_ids = group["model_id"].tolist()
            q_c = group["q_cal"].values
            selected = engine.select(q_c, model_ids, tier)
            actual_q = group.loc[group["model_id"] == selected, "quality_score"].values[0]
            selected_qualities.append(actual_q)
        tier_scores[tier] = float(np.mean(selected_qualities))

    total = sum(tier_weights[t] * tier_scores[t] for t in tier_scores)
    total /= sum(tier_weights.values())

    return {
        "holdout_mae": mae,
        "tier_scores": tier_scores,
        "weighted_score": total,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="최종 모델 빌드 + Holdout 평가")
    parser.add_argument("--data_path", required=True)
    parser.add_argument("--group_col", default="benchmark_id")
    parser.add_argument("--best_iteration", type=int, default=500,
                        help="OOF에서 결정된 최적 라운드 수")
    parser.add_argument("--output_dir", default="artifacts")
    args = parser.parse_args()

    if args.data_path.endswith(".parquet"):
        data = pd.read_parquet(args.data_path)
    else:
        data = pd.read_csv(args.data_path)

    with open(os.path.join(args.output_dir, "model_id_mapping.json")) as f:
        mapping = json.load(f)

    dev_data, holdout_data = create_dev_holdout_split(data, args.group_col)

    # Build final model
    build_final(dev_data, mapping, args.best_iteration, output_dir=args.output_dir)

    # Holdout evaluation
    results = evaluate_holdout(holdout_data, mapping, args.output_dir)

    print("\n=== Holdout Evaluation ===")
    print(f"  MAE: {results['holdout_mae']:.6f}")
    print(f"  Fast score:     {results['tier_scores']['fast']:.6f}")
    print(f"  Balanced score: {results['tier_scores']['balanced']:.6f}")
    print(f"  Premium score:  {results['tier_scores']['premium']:.6f}")
    print(f"  Weighted total: {results['weighted_score']:.6f}")

    with open(os.path.join(args.output_dir, "holdout_report.json"), "w") as f:
        json.dump(results, f, indent=2)
