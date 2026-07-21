# Efficient LLM Routing Challenge

이 저장소는 LLM 요청을 비용과 품질의 균형에 맞게 라우팅하는 실험 코드입니다.
현재 주 구현체는 `geometric_router/` 아래에 정리되어 있습니다.

## 구조

- `geometric_router/`: geometric router 패키지, 실행 스크립트, 테스트, 뷰어
- `geometric_router/README.md`: geometric router 시작 방법과 구현 설명
- `data/public/`: 공개 예제 학습 및 평가 데이터
- `artifacts/`: 학습된 router artifact와 실행 결과
- `quality_utility_router_baseline/`: 이전 quality-utility baseline 구현
- `docs/`: 아이디어와 구현 기록
- `scripts/`: 데이터 보정 등 공용 유틸리티 스크립트

## 빠른 시작

```powershell
pip install -r requirements.txt
python geometric_router\scripts\run_geometric_router.py train --no_tune
python geometric_router\scripts\run_geometric_router.py route "2 + 3의 값만 숫자로 답해줘." --tier fast
```

자세한 실행 방법은 `geometric_router/README.md`를 참고하세요.

## 테스트

```powershell
python -m pytest geometric_router\tests -q
```
