# 제출 체크리스트

## 제출 후보

최종 제출 라우터는 `router_impls/geometric/`이다. `quality_utility`와 다른 라우터는 비교와 검증용 baseline으로 유지한다.

## 필수 제출 파일

- 결과보고서 DOCX 또는 HWPX
- 동일 문서의 PDF 변환본
- `LICENSE`
- `docs/SBOM.md`
- `docs/AI_MODEL_USAGE.md`

결과보고서 작성 시 확인할 조건:

- 본문 5페이지 이내
- 맑은 고딕 10pt
- 안내문과 회색 placeholder 제거
- GitHub 공개 저장소 URL 입력
- YouTube 시연 영상 URL 입력

## 재현 명령

의존성 설치:

```powershell
pip install -r requirements.txt
```

전체 제출 검증:

```powershell
python scripts\run_submission_checks.py --full --output docs\report_assets\submission_check_run.json
```

개별 실행:

```powershell
python router_impls\geometric\scripts\train_geometric_router.py --policy_report artifacts\geometric_policy_report.json
python scripts\generate_report_assets.py --output_dir docs\report_assets
python scripts\generate_geometric_explanations.py --output_dir docs\report_assets
python scripts\generate_router_comparison.py --output_dir docs\report_assets
python scripts\measure_router_latency.py --output_dir docs\report_assets --repeat 3
python scripts\verify_submission_readiness.py --output docs\report_assets\submission_readiness.json
```

테스트:

```powershell
python -m pytest routing_stack\app\tests routing_stack\adapters\tests routing_stack\input\tests routing_stack\training\tests router_impls\geometric\tests -q
```

서버/뷰어:

```powershell
python routing_stack\app\router_server.py --ai mock --port 4100
python routing_stack\app\viewer_server.py --router_server_url http://127.0.0.1:4100 --port 4010
```

## 주요 진입점

- 학습: `router_impls/geometric/scripts/train_geometric_router.py`
- 단일 prompt 라우팅: `router_impls/geometric/scripts/route_geometric_prompt.py`
- 통합 CLI: `router_impls/geometric/scripts/run_geometric_router.py`
- public simulation: `router_impls/geometric/scripts/simulate_geometric_router.py`
- batch allocation: `router_impls/geometric/scripts/allocate_geometric_budget.py`
- 기본 report assets: `scripts/generate_report_assets.py`
- geometric decision 설명: `scripts/generate_geometric_explanations.py`
- baseline 비교: `scripts/generate_router_comparison.py`
- latency report: `scripts/measure_router_latency.py`
- readiness check: `scripts/verify_submission_readiness.py`
- reproducibility runner: `scripts/run_submission_checks.py`
- private adapter: `router_impls/geometric/submission.py`

## Private Simulator 인터페이스

```python
from router_impls.geometric.submission import create_router

router = create_router("artifacts/geometric_router.json")
decision = router.route(
    prompt=prompt,
    budget_tier=budget_tier,
    history=history,
    model_metadata=model_metadata,
)
```

`decision["action"]`은 다음 중 하나다.

- `{"type": "call_model", "model_id": "cheap|mid|premium"}`
- `{"type": "select_output", "model_id": "cheap|mid|premium", "history_index": 0}`
- `{"type": "abstain", "model_id": None}`

## 제출 수치

최신 public evaluation 기준:

- Overall weighted score: `0.532`
- Fast: mean_quality `0.885`, mean_cost `0.046`, under_route `12/73`, weighted_score `0.136`
- Balanced: mean_quality `0.926`, mean_cost `0.097`, under_route `0/73`, weighted_score `0.217`
- Premium: mean_quality `0.926`, mean_cost `0.099`, under_route `0/73`, weighted_score `0.179`
- Local decision latency: Fast `7.94ms`, Balanced `7.90ms`, Premium `7.95ms`

## Geometric 강점 확인 포인트

- `docs/report_assets/geometric_explanations.csv`에서 prompt별 후보 모델 cost, distance, pass probability, abstain probability를 확인한다.
- `docs/report_assets/router_comparison.csv`에서 always cheap/mid/premium baseline과 geometric router를 비교한다.
- 반복 prompt 케이스는 `repetition_ratio`와 `compressed_length_norm`으로 cheap 유지 근거를 확인한다.

## 최종 확인

- `docs/report_assets/submission_check_run.json`의 `status`가 `passed`인지 확인
- `docs/report_assets/submission_readiness.json`의 blocker가 실제 URL placeholder만 남았는지 확인
- `docs/SBOM.md`와 `requirements.txt`의 주요 라이브러리 일치 여부 확인
- 결과보고서에 `docs/report_assets/*.csv`의 최신 수치를 반영
- DOCX/HWPX와 PDF 파일명이 대회 규칙에 맞는지 확인
