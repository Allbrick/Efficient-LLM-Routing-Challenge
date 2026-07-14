# Efficient LLM Routing Challenge

이 저장소는 새로운 LLM 라우터 구현을 위해 구조를 정리하고 있습니다.

## 공통 참고 자료

- [챌린지 명세](PROJECT.md)
- [기존 구현 리뷰](docs/03-review/implementation-review.md)
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
