# Efficient LLM Routing Challenge

이 저장소는 새로운 LLM 라우터 구현을 위해 구조를 정리하고 있습니다.

## 공통 참고 자료

- [챌린지 명세](PROJECT.md)
- [기존 구현 리뷰](docs/03-review/implementation-review.md)
- [새로운 LLM Router 아이디어 3가지](docs/04-ideas/new-router-ideas.md)
- [기하학적 LLM Router 아이디어](docs/04-ideas/geometric-router-ideas.md)
- [공개 샘플 데이터](data/public)

## 기존 베이스라인

- [Quality Utility Router Baseline](quality_utility_router_baseline)

이 베이스라인은 이전 라우터 구현입니다. 후보 모델별 품질을 예측하고,
예측값을 보정한 뒤, 프롬프트 prior와 budget tier별 utility를 적용해
최종 모델을 선택합니다.

새 라우터를 설계하기 전에
[기존 구현 리뷰](docs/03-review/implementation-review.md)를 먼저 확인해야 합니다.
해당 문서에는 잘 만든 점, 잘못 설계된 점, 다음 구현에서 반복하지 말아야 할
문제들이 정리되어 있습니다.

## 새 Geometric Router 실행

새 구현은 루트의 `geometric_router/`와 `scripts/`에 있습니다.

의존성 설치:

```powershell
pip install -r requirements.txt
```

학습:

```powershell
python scripts\train_geometric_router.py
```

단일 프롬프트 라우팅:

```powershell
python scripts\route_geometric_prompt.py "2 + 3의 값만 숫자로 답해줘." --tier balanced --task_type math_exact --difficulty trivial --risk_level low --evaluation_type exact_match
```

테스트:

```powershell
python -m pytest tests -q
```
