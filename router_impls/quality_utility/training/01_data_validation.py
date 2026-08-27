"""Step 1: 공개 데이터 정합성 검증.

사용법:
    python -m training.01_data_validation --data_path data/public/

검증 항목:
    - 모든 prompt에 동일 후보 모델 결과가 있는지
    - quality 척도가 모델 간 비교 가능한지
    - 결측/중복/범위 오류 확인
"""

import argparse
import sys

import pandas as pd


def validate(data: pd.DataFrame) -> dict:
    """데이터 정합성을 검증하고 결과를 반환한다."""
    report = {"errors": [], "warnings": [], "stats": {}}

    # 필수 컬럼 확인
    required_cols = ["prompt_id", "prompt", "model_id", "quality_score"]
    missing = [c for c in required_cols if c not in data.columns]
    if missing:
        report["errors"].append(f"필수 컬럼 누락: {missing}")
        return report

    # 기본 통계
    report["stats"]["n_rows"] = len(data)
    report["stats"]["n_prompts"] = data["prompt_id"].nunique()
    report["stats"]["n_models"] = data["model_id"].nunique()
    report["stats"]["models"] = sorted(data["model_id"].unique().tolist())

    # 결측값
    null_counts = data[required_cols].isnull().sum()
    for col, cnt in null_counts.items():
        if cnt > 0:
            report["errors"].append(f"결측값 발견: {col}에 {cnt}개")

    # 프롬프트별 모델 수 일관성
    models_per_prompt = data.groupby("prompt_id")["model_id"].nunique()
    n_models = data["model_id"].nunique()
    inconsistent = models_per_prompt[models_per_prompt != n_models]
    if len(inconsistent) > 0:
        report["warnings"].append(
            f"모델 수 불일치 프롬프트: {len(inconsistent)}개 "
            f"(기대: {n_models}, 범위: {inconsistent.min()}-{inconsistent.max()})"
        )

    # quality_score 범위
    q_min = data["quality_score"].min()
    q_max = data["quality_score"].max()
    report["stats"]["quality_range"] = [float(q_min), float(q_max)]
    if q_min < 0 or q_max > 1:
        report["warnings"].append(
            f"quality_score 범위가 [0,1] 밖: [{q_min:.4f}, {q_max:.4f}]"
        )

    # 중복 행
    dupes = data.duplicated(subset=["prompt_id", "model_id"]).sum()
    if dupes > 0:
        report["errors"].append(f"중복 (prompt_id, model_id) 쌍: {dupes}개")

    # 모델별 quality 분포
    model_stats = data.groupby("model_id")["quality_score"].agg(["mean", "std", "min", "max"])
    report["stats"]["model_quality"] = model_stats.to_dict("index")

    # cost 컬럼이 있으면 비용 분석
    if "cost" in data.columns:
        cost_stats = data.groupby("model_id")["cost"].agg(["mean", "std", "min", "max"])
        report["stats"]["model_cost"] = cost_stats.to_dict("index")

    return report


def print_report(report: dict) -> None:
    print("\n=== Data Validation Report ===\n")

    print(f"  Total rows:    {report['stats'].get('n_rows', 'N/A')}")
    print(f"  Unique prompts: {report['stats'].get('n_prompts', 'N/A')}")
    print(f"  Unique models:  {report['stats'].get('n_models', 'N/A')}")
    print(f"  Models:         {report['stats'].get('models', 'N/A')}")
    print(f"  Quality range:  {report['stats'].get('quality_range', 'N/A')}")

    if report["errors"]:
        print(f"\n  ERRORS ({len(report['errors'])}):")
        for e in report["errors"]:
            print(f"    [X] {e}")

    if report["warnings"]:
        print(f"\n  WARNINGS ({len(report['warnings'])}):")
        for w in report["warnings"]:
            print(f"    [!] {w}")

    if "model_quality" in report["stats"]:
        print("\n  Model Quality Distribution:")
        for model, stats in report["stats"]["model_quality"].items():
            print(f"    {model}: mean={stats['mean']:.4f} std={stats['std']:.4f} "
                  f"[{stats['min']:.4f}, {stats['max']:.4f}]")

    if not report["errors"] and not report["warnings"]:
        print("\n  All checks passed.")

    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="공개 데이터 정합성 검증")
    parser.add_argument("--data_path", required=True, help="CSV 또는 parquet 경로")
    args = parser.parse_args()

    if args.data_path.endswith(".parquet"):
        data = pd.read_parquet(args.data_path)
    else:
        data = pd.read_csv(args.data_path)

    report = validate(data)
    print_report(report)

    if report["errors"]:
        sys.exit(1)
