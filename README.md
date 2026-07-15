# Efficient LLM Routing Challenge

로컬 코드만으로 동작하는 LLM router 구현입니다. 현재 제출 후보는 `geometric_router/`이며, 기존 `quality_utility_router_baseline/`은 비교용 레거시 baseline으로 분리해 둡니다.

## 구조

- `geometric_router/`: 새 geometric router 구현
- `geometric_router/submission.py`: private simulator 대응용 adapter
- `scripts/`: 학습, 라우팅, 시뮬레이션, allocation, viewer 실행 진입점
- `data/public/`: public 학습/평가 예시 데이터
- `artifacts/`: 재생성 가능한 router artifact와 labels
- `geometric_viewer/`: 라우팅 및 batch allocation 확인용 viewer
- `quality_utility_router_baseline/`: 이전 quality-utility baseline
- `docs/`: 구현 리뷰와 아이디어 문서

## 설치

```powershell
pip install -r requirements.txt
```

## 실행 진입점

통합 진입점:

```powershell
python scripts\run_geometric_router.py train --no_tune
python scripts\run_geometric_router.py route "2 + 3의 값만 숫자로 답해줘." --tier fast
python scripts\run_geometric_router.py simulate --tier fast
python scripts\run_geometric_router.py allocate --tier fast
python scripts\run_geometric_router.py viewer --port 4010
```

개별 스크립트도 그대로 사용할 수 있습니다.

## Artifact 재생성

기본 artifact와 labels를 재생성합니다.

```powershell
python scripts\train_geometric_router.py --no_tune
```

생성물:

- `artifacts/geometric_router.json`
- `artifacts/geometric_labels.csv`

주의: 현재 `tune_geometric_policy.py`는 이전 simulation objective 기준입니다. 새 batch allocator objective와 완전히 맞추려면 tuning loss를 별도로 갱신해야 합니다. 제출 검증 기준 artifact는 우선 `--no_tune`로 재생성합니다.

## 테스트

```powershell
python -m pytest tests -q
```

## Public Simulation

전체 public set tier별 independent routing simulation:

```powershell
python scripts\simulate_geometric_router.py
```

Fast tier batch allocation:

```powershell
python scripts\allocate_geometric_budget.py --tier fast
```

Batch allocation은 총 tier 예산 안에서 프롬프트별 action을 고릅니다. summary에는 `under_route`, `over_route`, `under_route_lower_bound`, `mean_expected_quality`, `mean_quality_gain_per_cost`가 포함됩니다.

## Viewer

```powershell
python scripts\serve_geometric_viewer.py --host 127.0.0.1 --port 4010
```

브라우저에서 `http://127.0.0.1:4010/` 접속.

Viewer 기능:

- 단일 프롬프트 라우팅
- 후보별 `pass_probability`, `sufficiency_probability` 시각화
- public simulation summary
- batch allocation 결과 표
- under/over-route 필터

## Baseline과 새 Router 역할

`quality_utility_router_baseline/`은 이전 방식입니다. 품질 예측값에서 비용 패널티를 빼는 scalar utility 구조라서, lambda와 threshold 가정에 민감합니다.

`geometric_router/`는 새 구현입니다.

- evidence vector 기반 feasibility envelope
- cheapest-passing 확률 모델
- sufficiency risk model
- `abstain` action
- JSON schema 기반 evaluator
- batch budget allocator

새 구현을 수정할 때 baseline 폴더는 비교 대상으로만 유지합니다.

## Private Simulator 대응 인터페이스

private simulator에서는 다음 adapter를 사용할 수 있습니다.

```python
from geometric_router.submission import RouterSubmission

router = RouterSubmission("artifacts/geometric_router.json")
result = router.route(
    prompt="이 세상 모든 코드를 가져와줘.",
    budget_tier="fast",
    history=[],
    model_metadata=[],
)

print(result["action"])
```

반환 예:

```json
{
  "action": {
    "type": "abstain",
    "model_id": null
  },
  "selected_model_id": "abstain",
  "selection_reason": "abstain_probability"
}
```

모델 호출이 필요한 경우:

```json
{
  "action": {
    "type": "call_model",
    "model_id": "cheap"
  }
}
```

외부 API나 네트워크 호출은 하지 않습니다.
