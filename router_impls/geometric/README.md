# Geometric Router

`router_impls.geometric`는 라우터 구현체입니다. 일반 실행 흐름에서는 공통 스택을 통해 사용합니다.

```text
viewer -> router -> ai
```

## 공통 스택 실행

프로젝트 루트에서 실행합니다.

```powershell
python routing_stack\app\router_server.py --ai mock --port 4100
python routing_stack\app\viewer_server.py --router_server_url http://127.0.0.1:4100 --port 4010
```

Ollama를 붙여 실행합니다.

```powershell
python routing_stack\app\router_server.py --ai ollama --port 4100
python routing_stack\app\viewer_server.py --router_server_url http://127.0.0.1:4100 --port 4010
```

브라우저에서 `http://127.0.0.1:4010/`에 접속합니다.

## Geometric 전용 명령

`router_impls/geometric/` 폴더 안에서 의존성을 설치합니다.

```powershell
pip install -r requirements.txt
```

학습과 geometric 전용 도구를 실행합니다.

```powershell
python scripts\run_geometric_router.py train --no_tune
python scripts\run_geometric_router.py route "2 + 3의 값만 숫자로 답해줘." --tier fast
python scripts\run_geometric_router.py simulate --tier fast
python scripts\run_geometric_router.py allocate --tier fast
```

생성 파일:

- `../../artifacts/geometric_router.json`
- `../../artifacts/geometric_labels.csv`

## 구성 요소

- `router.py`: 핵심 라우팅 의사결정
- `submission.py`: private simulator adapter
- `features.py`: 프롬프트 evidence 추출
- `evaluator.py`: 학습 라벨용 출력 평가기
- `budget_allocator.py`: 예산 내 batch allocation
- `simulator.py`: 공개 예제 시뮬레이션
- `tuning.py`: 정책 튜닝
- `scripts/`: geometric 전용 CLI 도구
- `tests/`: 테스트

## 테스트

`router_impls/geometric/` 폴더에서 실행합니다.

```powershell
python -m pytest tests -q
```

프로젝트 루트에서는 다음처럼 실행합니다.

```powershell
python -m pytest router_impls\geometric\tests -q
```


