"""Step 3: GroupKFold OOF 학습.

사용법:
    python -m training.03_train_oof --data_path data/public/train.csv

산출물:
    - artifacts/oof_predictions.csv
    - 학습 로그 (fold별 MAE)
"""

import argparse
import json
import os

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from src.feature_extractor import FeatureExtractor
from src.candidate_expander import CandidateExpander
from src.quality_predictor import QualityPredictor


def create_dev_holdout_split(
    data: pd.DataFrame,
    group_col: str,
    dev_ratio: float = 0.8,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Development / Final Holdout 그룹 분리."""
    groups = np.array(data[group_col].unique())
    rng = np.random.RandomState(random_state)
    rng.shuffle(groups)

    n_dev = int(len(groups) * dev_ratio)
    dev_groups = set(groups[:n_dev])

    dev_mask = data[group_col].isin(dev_groups)
    return data[dev_mask].copy(), data[~dev_mask].copy()


def train_oof(
    dev_data: pd.DataFrame,
    group_col: str,
    model_id_mapping: dict,
    n_folds: int = 5,
    tfidf_max_features: int = 5000,
    svd_n_components: int = 50,
    lgbm_params: dict | None = None,
) -> tuple[np.ndarray, dict]:
    """GroupKFold OOF predictions를 생성한다."""

    oof_preds = np.full(len(dev_data), np.nan)
    fold_metrics = []
    expander = CandidateExpander(model_id_mapping)
    model_id_col_name = "model_id"
    candidate_ids = sorted(model_id_mapping.keys())

    gkf = GroupKFold(n_splits=n_folds)
    groups = dev_data[group_col].values

    # prompt 단위로 split (long-format이므로 prompt_id 기준)
    prompt_ids = dev_data["prompt_id"].values
    unique_prompt_ids = dev_data["prompt_id"].unique()
    prompt_groups = dev_data.drop_duplicates("prompt_id").set_index("prompt_id")[group_col]

    for fold_idx, (train_prompt_idx, val_prompt_idx) in enumerate(
        gkf.split(unique_prompt_ids, groups=prompt_groups.loc[unique_prompt_ids].values)
    ):
        train_pids = set(unique_prompt_ids[train_prompt_idx])
        val_pids = set(unique_prompt_ids[val_prompt_idx])

        train_mask = dev_data["prompt_id"].isin(train_pids)
        val_mask = dev_data["prompt_id"].isin(val_pids)

        train_fold = dev_data[train_mask]
        val_fold = dev_data[val_mask]

        print(f"\n--- Fold {fold_idx + 1}/{n_folds} ---")
        print(f"  Train: {len(train_fold)} rows ({len(train_pids)} prompts)")
        print(f"  Val:   {len(val_fold)} rows ({len(val_pids)} prompts)")

        # 1. Feature Pipeline (train에서만 fit)
        train_prompts = train_fold.drop_duplicates("prompt_id")["prompt"].tolist()
        extractor = FeatureExtractor(
            tfidf_max_features=tfidf_max_features,
            svd_n_components=svd_n_components,
        )
        extractor.fit(train_prompts)

        # 2. Feature 생성 + Candidate Expansion
        def build_features(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
            unique_df = df.drop_duplicates("prompt_id")
            prompt_feats = extractor.transform(unique_df["prompt"].tolist())
            pid_to_idx = {pid: i for i, pid in enumerate(unique_df["prompt_id"])}

            rows = []
            for _, row in df.iterrows():
                p_idx = pid_to_idx[row["prompt_id"]]
                mid_encoded = model_id_mapping[row[model_id_col_name]]
                feat = np.append(prompt_feats[p_idx], mid_encoded)
                rows.append(feat)

            X = np.array(rows, dtype=np.float32)
            y = df["quality_score"].values.astype(np.float32)
            return X, y

        X_train, y_train = build_features(train_fold)
        X_val, y_val = build_features(val_fold)

        # 3. LightGBM 학습
        cat_col = [X_train.shape[1] - 1]  # model_id는 마지막 컬럼
        predictor = QualityPredictor(lgbm_params)
        metrics = predictor.train(
            X_train, y_train, X_val, y_val,
            categorical_feature=cat_col,
        )

        print(f"  Best iteration: {metrics['best_iteration']}")
        print(f"  Val MAE: {metrics['best_val_mae']:.6f}")
        fold_metrics.append(metrics)

        # 4. Val 예측
        val_indices = np.where(val_mask)[0]
        oof_preds[val_indices] = predictor.predict(X_val)

    overall_mae = float(np.nanmean(np.abs(dev_data["quality_score"].values - oof_preds)))
    print(f"\n=== OOF MAE: {overall_mae:.6f} ===")

    return oof_preds, {
        "n_folds": n_folds,
        "fold_metrics": fold_metrics,
        "overall_mae": overall_mae,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GroupKFold OOF 학습")
    parser.add_argument("--data_path", required=True)
    parser.add_argument("--group_col", default="benchmark_id")
    parser.add_argument("--n_folds", type=int, default=5)
    parser.add_argument("--output_dir", default="artifacts")
    args = parser.parse_args()

    if args.data_path.endswith(".parquet"):
        data = pd.read_parquet(args.data_path)
    else:
        data = pd.read_csv(args.data_path)

    model_ids = sorted(data["model_id"].unique())
    model_id_mapping = {mid: i for i, mid in enumerate(model_ids)}
    print(f"Model ID mapping: {model_id_mapping}")

    # Dev/Holdout split
    dev_data, holdout_data = create_dev_holdout_split(data, args.group_col)
    print(f"Dev: {len(dev_data)} rows, Holdout: {len(holdout_data)} rows")

    # OOF Training
    oof_preds, report = train_oof(
        dev_data, args.group_col, model_id_mapping, n_folds=args.n_folds,
    )

    # Save
    os.makedirs(args.output_dir, exist_ok=True)
    dev_data = dev_data.copy()
    dev_data["oof_q_hat"] = oof_preds
    dev_data.to_csv(os.path.join(args.output_dir, "oof_predictions.csv"), index=False)
    holdout_data.to_csv(os.path.join(args.output_dir, "holdout_data.csv"), index=False)

    with open(os.path.join(args.output_dir, "model_id_mapping.json"), "w") as f:
        json.dump(model_id_mapping, f, indent=2)

    print(f"\nSaved to {args.output_dir}/")
