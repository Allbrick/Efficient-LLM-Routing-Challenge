"""Step 2: Oracle 분석.

사용법:
    python -m training.02_oracle_analysis --data_path data/public/train.csv

산출물:
    - Quality Oracle (비용 무관 최대 품질)
    - Policy Oracle (lambda frontier)
    - Lambda 전환점 분포 분석
"""

import argparse
import json

import numpy as np
import pandas as pd


def compute_quality_oracle(data: pd.DataFrame) -> pd.DataFrame:
    """각 prompt에 대해 비용 무관 최대 품질 모델을 찾는다."""
    idx = data.groupby("prompt_id")["quality_score"].idxmax()
    oracle = data.loc[idx, ["prompt_id", "model_id", "quality_score"]].copy()
    oracle.rename(columns={
        "model_id": "oracle_model_id",
        "quality_score": "oracle_quality",
    }, inplace=True)
    return oracle.reset_index(drop=True)


def compute_transition_points(data: pd.DataFrame, cost_col: str = "cost") -> np.ndarray:
    """모든 (prompt, model_a, model_b) 쌍에서 선택이 전환되는 lambda*를 계산한다.

    lambda* = (Q_b - Q_a) / (C_b - C_a)
    단, C_b != C_a이고 lambda* > 0인 경우만 유효.
    """
    transitions = []
    models = sorted(data["model_id"].unique())

    for pid, group in data.groupby("prompt_id"):
        model_data = {row["model_id"]: row for _, row in group.iterrows()}
        for i, m_a in enumerate(models):
            for m_b in models[i + 1:]:
                if m_a not in model_data or m_b not in model_data:
                    continue
                q_a = model_data[m_a]["quality_score"]
                q_b = model_data[m_b]["quality_score"]
                c_a = model_data[m_a][cost_col]
                c_b = model_data[m_b][cost_col]

                delta_c = c_b - c_a
                if abs(delta_c) < 1e-12:
                    continue
                lam_star = (q_b - q_a) / delta_c
                if lam_star > 0:
                    transitions.append(lam_star)

    return np.array(transitions)


def compute_policy_oracle(
    data: pd.DataFrame,
    lambda_values: np.ndarray,
    cost_col: str = "cost",
) -> pd.DataFrame:
    """각 lambda 값에서 각 prompt의 최적 모델을 역산한다."""
    results = []
    # 비용 정규화
    c_min = data[cost_col].min()
    c_max = data[cost_col].max()
    c_range = c_max - c_min if c_max > c_min else 1.0
    data = data.copy()
    data["cost_norm"] = (data[cost_col] - c_min) / c_range

    for lam in lambda_values:
        data["utility"] = data["quality_score"] - lam * data["cost_norm"]
        idx = data.groupby("prompt_id")["utility"].idxmax()
        best = data.loc[idx, ["prompt_id", "model_id", "quality_score", "utility"]].copy()
        best["lambda"] = lam
        results.append(best)

    return pd.concat(results, ignore_index=True)


def analyze_and_report(data: pd.DataFrame, cost_col: str = "cost") -> dict:
    """전체 Oracle 분석을 수행하고 결과를 반환한다."""
    report = {}

    # 1. Quality Oracle
    q_oracle = compute_quality_oracle(data)
    report["quality_oracle"] = {
        "mean_quality": float(q_oracle["oracle_quality"].mean()),
        "model_distribution": q_oracle["oracle_model_id"].value_counts().to_dict(),
    }

    # 2. Transition points
    transitions = compute_transition_points(data, cost_col)
    if len(transitions) > 0:
        quantiles = np.percentile(transitions, [5, 25, 50, 75, 95])
        report["transition_points"] = {
            "count": int(len(transitions)),
            "P5": float(quantiles[0]),
            "P25": float(quantiles[1]),
            "P50": float(quantiles[2]),
            "P75": float(quantiles[3]),
            "P95": float(quantiles[4]),
            "suggested_lambda_range": [float(quantiles[0] * 0.5), float(quantiles[4] * 1.5)],
        }
    else:
        report["transition_points"] = {"count": 0, "suggested_lambda_range": [0.0, 5.0]}

    # 3. Policy Oracle frontier
    lam_range = report["transition_points"]["suggested_lambda_range"]
    lambda_values = np.linspace(lam_range[0], lam_range[1], 20)
    policy = compute_policy_oracle(data, lambda_values, cost_col)

    model_selection_by_lambda = {}
    for lam, group in policy.groupby("lambda"):
        dist = group["model_id"].value_counts(normalize=True).to_dict()
        model_selection_by_lambda[f"lambda={lam:.2f}"] = dist
    report["policy_frontier_sample"] = model_selection_by_lambda

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Oracle 분석")
    parser.add_argument("--data_path", required=True)
    parser.add_argument("--cost_col", default="cost")
    parser.add_argument("--output", default="artifacts/oracle_analysis.json")
    args = parser.parse_args()

    if args.data_path.endswith(".parquet"):
        data = pd.read_parquet(args.data_path)
    else:
        data = pd.read_csv(args.data_path)

    report = analyze_and_report(data, args.cost_col)

    import os
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nOracle Analysis saved to: {args.output}")
    print(f"  Quality Oracle mean: {report['quality_oracle']['mean_quality']:.4f}")
    print(f"  Model distribution: {report['quality_oracle']['model_distribution']}")
    tp = report["transition_points"]
    print(f"  Transition points: {tp['count']} found")
    if tp["count"] > 0:
        print(f"    P5={tp['P5']:.4f} P50={tp['P50']:.4f} P95={tp['P95']:.4f}")
    print(f"  Suggested lambda range: {tp['suggested_lambda_range']}")
