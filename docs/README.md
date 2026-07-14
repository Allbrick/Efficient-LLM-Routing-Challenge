# 프로젝트 문서

## 리뷰

- [기존 구현 리뷰](03-review/implementation-review.md)

이 리뷰 문서는 다음 라우터 설계에서 계속 참고하기 위한 장기 문서입니다.
이전 베이스라인이 어떻게 구현되었는지, 어떤 부분은 유지할 만한지, 어떤 설계는
복사하지 말고 고쳐야 하는지 정리합니다.

## 아이디어

- [새로운 LLM Router 아이디어 3가지](04-ideas/new-router-ideas.md)
- [기하학적 LLM Router 아이디어](04-ideas/geometric-router-ideas.md)

새 라우터의 초기 방향을 잡기 위한 아이디어 문서입니다. 기존 라우터의 단점인
수동 prior 증가, `quality_score` 중심 학습, 출력 검증 부재를 반복하지 않는 접근을
정리합니다.
