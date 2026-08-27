# Quality Utility Router Baseline

이 폴더는 이전 라우터 구현을 보관합니다. 현재 구현은 후보 모델별 품질을
예측하고, 예측값을 보정한 뒤, 프롬프트 prior와 budget tier별 utility를 적용해
가장 적합한 후보 모델을 선택하는 방식입니다.

저장소 루트는 다음 라우터 설계에 사용하고, 이 폴더는 실행 가능한 기존
베이스라인으로 유지합니다. `PROJECT.md`, `data/`처럼 새 구현에도 동일하게
적용되는 공통 자료는 루트에 둡니다.

## 실행 방법

아래 명령은 `router_impls.quality_utility` 폴더에서 실행합니다.

```powershell
pip install -r requirements.txt
python -m pytest -q
```

## 베이스라인 파이프라인 재생성

```powershell
python -m training.01_data_validation --data_path ../data/public/example_train.csv
python -m training.02_oracle_analysis --data_path ../data/public/example_train.csv
python -m training.03_train_oof --data_path ../data/public/example_train.csv
python -m training.04_calibration --oof_path artifacts/oof_predictions.csv
python -m training.05_lambda_optimize --data_path ../data/public/example_train.csv
python -m training.06_final_build --data_path ../data/public/example_train.csv --best_iteration 64
python -m training.07_feedback_tune
python scripts/build_viewer_data.py
```

## Viewer 실행

```powershell
python scripts/serve_router_viewer.py --port 4003
```

그다음 아래 주소를 엽니다.

```text
http://127.0.0.1:4003/
```

## 현재 설계 상태

이 버전은 동작하는 베이스라인으로는 유용하지만, 다음 구현의 기반으로 그대로
사용하기에는 부족합니다. 가장 큰 한계는 라우팅 판단이 아직 작은 학습 데이터,
수동 프롬프트 prior, feedback 규칙에 많이 의존한다는 점입니다. 다음 라우터는
객관적 evaluator, pass/fail 근거, 명시적인 budget-aware risk handling 쪽으로
판단 기준을 옮겨야 합니다.

이 베이스라인은 `router_impls/geometric/`과의 비교 대상으로만 유지합니다.
비교 결과는 `docs/report_assets/router_comparison*.csv`에 있습니다.

