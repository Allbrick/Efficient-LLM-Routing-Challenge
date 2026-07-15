# 제출 구조 정리

## 제출 후보

현재 제출 후보는 `geometric_router/`입니다.

`quality_utility_router_baseline/`은 비교와 회귀 검토용 레거시 baseline입니다. 제출 로직에 직접 사용하지 않습니다.

## 재현 명령

```powershell
pip install -r requirements.txt
python scripts\train_geometric_router.py --no_tune
python -m pytest tests -q
python scripts\allocate_geometric_budget.py --tier fast
```

## 주요 진입점

- 학습: `scripts/train_geometric_router.py`
- 단일 라우팅: `scripts/route_geometric_prompt.py`
- 통합 CLI: `scripts/run_geometric_router.py`
- public simulation: `scripts/simulate_geometric_router.py`
- batch allocation: `scripts/allocate_geometric_budget.py`
- viewer: `scripts/serve_geometric_viewer.py`
- private adapter: `geometric_router/submission.py`

## Private Simulator 인터페이스

```python
from geometric_router.submission import create_router

router = create_router("artifacts/geometric_router.json")
decision = router.route(
    prompt=prompt,
    budget_tier=budget_tier,
    history=history,
    model_metadata=model_metadata,
)
```

`decision["action"]`은 다음 중 하나입니다.

- `{"type": "call_model", "model_id": "cheap|mid|premium"}`
- `{"type": "abstain", "model_id": None}`

## 남은 정리 항목

- `tune_geometric_policy.py`의 loss를 새 allocator objective와 일치시키기
- private simulator가 요구하는 정확한 함수명/파일명이 공개되면 `submission.py` adapter 이름 맞추기
- public 데이터가 더 커지면 task classifier calibration 별도 검증 추가
