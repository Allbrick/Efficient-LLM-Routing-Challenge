# Geometric Router

`geometric_router`는 프롬프트별 evidence vector를 만들고, 각 모델이 잘 처리할 수 있는 영역을 geometric envelope로 학습한 뒤 가장 저렴하면서 충분한 모델을 선택하는 LLM 라우터입니다.

## 폴더 구조

- `router.py`: 라우팅 의사결정의 핵심 구현
- `submission.py`: private simulator 연결용 adapter
- `features.py`: 프롬프트 evidence vector 추출
- `evaluator.py`: 학습 라벨 생성을 위한 출력 평가기
- `budget_allocator.py`: 전체 예산 안에서 batch routing action 배분
- `simulator.py`: public sample set 시뮬레이션
- `tuning.py`: tier별 라우팅 정책 튜닝
- `scripts/`: 학습, 라우팅, 시뮬레이션, 뷰어 실행 진입점
- `tests/`: geometric router 테스트
- `viewer/`: 브라우저에서 라우팅 결과를 확인하는 정적 UI

## 설치

`geometric_router/` 폴더 안에 있다면 다음처럼 설치합니다.

```powershell
pip install -r requirements.txt
```

프로젝트 루트에 있다면 다음 명령도 가능합니다.

```powershell
pip install -r requirements.txt
```

## 시작 방법

`geometric_router/` 폴더 안에서 실행하는 경우:

```powershell
python scripts\run_geometric_router.py train --no_tune
python scripts\run_geometric_router.py route "2 + 3의 값만 숫자로 답해줘." --tier fast
python scripts\run_geometric_router.py simulate --tier fast
python scripts\run_geometric_router.py allocate --tier fast
python scripts\run_geometric_router.py viewer --port 4010
```

프로젝트 루트에서 실행하는 경우:

```powershell
python geometric_router\scripts\run_geometric_router.py train --no_tune
python geometric_router\scripts\run_geometric_router.py route "2 + 3의 값만 숫자로 답해줘." --tier fast
python geometric_router\scripts\run_geometric_router.py simulate --tier fast
python geometric_router\scripts\run_geometric_router.py allocate --tier fast
python geometric_router\scripts\run_geometric_router.py viewer --port 4010
```

뷰어는 실행 후 브라우저에서 `http://127.0.0.1:4010/`로 접속합니다.

## 개별 명령

아래 명령은 `geometric_router/` 폴더 안에서 실행하는 기준입니다.

```powershell
python scripts\train_geometric_router.py --no_tune
python scripts\route_geometric_prompt.py "간단한 정렬 함수를 파이썬으로 작성해줘." --tier balanced
python scripts\simulate_geometric_router.py
python scripts\allocate_geometric_budget.py --tier fast
```

생성 파일:

- `../artifacts/geometric_router.json`
- `../artifacts/geometric_labels.csv`

## 동작 개요

1. `features.py`가 프롬프트 길이, 정확 답변 여부, 위험도, 평가 유형 같은 신호를 evidence vector로 변환합니다.
2. `evaluator.py`가 학습 데이터의 모델 응답을 평가해 각 모델의 성공 라벨을 만듭니다.
3. `router.py`가 모델별 성공 샘플 영역을 envelope로 학습하고, pass probability와 sufficiency risk를 함께 계산합니다.
4. 라우팅 시 `abstain`, `cheap`, `mid`, `premium` 후보를 비교해 tier 예산과 통과 가능성에 맞는 action을 선택합니다.
5. `budget_allocator.py`는 개별 라우팅 결과를 전체 예산 제약에 맞춰 다시 배분합니다.

## 테스트

`geometric_router/` 폴더 안에서 실행합니다.

```powershell
python -m pytest tests -q
```

프로젝트 루트에서는 다음처럼 실행합니다.

```powershell
python -m pytest geometric_router\tests -q
```

## Private Simulator Adapter

private simulator에서는 `RouterSubmission`을 사용합니다.

```python
from geometric_router.submission import RouterSubmission

router = RouterSubmission("artifacts/geometric_router.json")
result = router.route(
    prompt="불가능한 요청이면 거절해줘.",
    budget_tier="fast",
    history=[],
    model_metadata=[],
)

print(result["action"])
```

반환 action은 모델 호출 또는 abstain입니다.

```json
{
  "action": {
    "type": "call_model",
    "model_id": "cheap"
  }
}
```

```json
{
  "action": {
    "type": "abstain",
    "model_id": null
  }
}
```
