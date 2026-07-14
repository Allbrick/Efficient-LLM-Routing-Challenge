# 기하학적 LLM Router 아이디어

이 문서는 기존 `quality_score - lambda * cost` 방식의 한계를 다차원 공간 모델로
보완하는 방향을 정리합니다.

기존 방식의 핵심 문제는 품질과 비용의 trade-off를 하나의 스칼라 점수로 접어버린다는
점입니다.

```text
utility = quality - lambda * cost
```

이 식은 단순하지만, 라우팅 문제를 지나치게 1차원화합니다. 실제로는 비용, 품질,
난이도, 위험도, 조건 수, 도메인, 검증 가능성이 함께 작동합니다. 따라서 새 접근은
라우팅을 “직선 위의 최대값 찾기”가 아니라 “공간 안에서 가능한 영역 찾기”로
바꿉니다.

## 1. Cost-Quality 파레토 프론티어

`lambda` 하나로 비용-품질 trade-off를 표현하지 않고, `(cost, quality)` 평면에서
파레토 프론티어를 학습합니다.

기본 아이디어는 다음입니다.

```text
1. 각 모델 선택 결과를 (cost, quality) 점으로 배치
2. 다른 점에 의해 지배되는 점 제거
3. non-dominated 점들로 frontier 구성
4. budget limit 안에서 도달 가능한 최대 quality 선택
```

어떤 점 A가 점 B보다 비용은 낮거나 같고 품질은 높거나 같다면, B는 지배당한
점입니다. 이런 점은 라우팅 후보에서 제거할 수 있습니다.

```text
A = cost 0.05, quality 0.91
B = cost 0.20, quality 0.89

=> B는 A에게 지배당함
```

이 방식의 장점은 `lambda`를 고정하지 않아도 된다는 점입니다. 프론티어 자체가
비선형이면 Fast, Balanced, Premium 구간마다 자연스럽게 다른 기울기를 갖습니다.

```text
낮은 예산 구간:
  작은 비용 증가로 품질이 크게 개선될 수 있음

높은 예산 구간:
  비용을 많이 써도 품질 개선이 작을 수 있음
```

즉 라우터는 더 이상 “이 tier의 lambda는 얼마인가?”를 묻지 않습니다.

대신 다음을 묻습니다.

```text
이 budget 안에서 파레토 프론티어상 가장 좋은 선택은 무엇인가?
```

## 2. Difficulty-Risk 능력 영역

기존 threshold 방식은 보통 이런 형태입니다.

```text
if difficulty_score < 0.3:
    cheap
elif difficulty_score < 0.7:
    mid
else:
    premium
```

하지만 난이도 하나만으로는 부족합니다. 짧지만 위험한 프롬프트도 있고, 길지만
정답이 명확한 프롬프트도 있습니다.

따라서 `(difficulty_score, risk_score)` 2D 평면을 만들고, 각 모델 또는 tier가
과거에 성공했던 영역을 학습합니다.

```text
x축: difficulty_score
y축: risk_score
```

각 tier의 성공 샘플을 이 평면에 찍으면, cheap이 잘 처리하는 영역, mid가 필요한
영역, premium이 필요한 영역이 생깁니다.

라우팅은 다음처럼 할 수 있습니다.

```text
1. 새 프롬프트의 좌표 x = (difficulty, risk) 계산
2. cheap 성공 영역 안에 있으면 cheap 선택
3. 아니면 mid 영역 확인
4. 아니면 premium 영역 확인
```

이 방식은 단순 threshold보다 표현력이 높습니다. 경계가 직선 하나가 아니라
다각형, 타원, 밀도 영역이 될 수 있기 때문입니다.

예를 들어 다음 두 프롬프트는 길이만 보면 비슷하게 보일 수 있지만, 공간 좌표는
달라야 합니다.

```text
"HTTP의 기본 포트 번호는?"
  difficulty 낮음, risk 낮음

"이 계약의 면책 조항이 무효인지 판단해줘."
  difficulty 불명확, risk 높음, 입력 부족
```

이 구조는 Evidence-First Router와 자연스럽게 연결됩니다. Evidence-First 계층이
`difficulty_score`, `risk_score`, `missing_context`, `condition_count` 같은 좌표를
만들고, 기하학적 라우터가 그 좌표가 어느 능력 영역에 들어가는지 판단합니다.

## 3. 마할라노비스 거리 기반 Feasibility Envelope

각 tier의 능력 영역을 딱딱한 다각형으로 만들 수도 있지만, 더 통계적인 방식은
타원 영역으로 모델링하는 것입니다.

각 tier가 과거에 잘 처리했던 프롬프트들의 feature 분포를 추정합니다.

```text
mu_tier    = 성공 샘플 feature 평균
Sigma_tier = 성공 샘플 feature 공분산
```

새 프롬프트 `x`가 해당 tier의 성공 분포에서 얼마나 떨어져 있는지는 마할라노비스
거리로 계산합니다.

```text
D_M(x, tier) = sqrt((x - mu_tier)^T * Sigma_tier^-1 * (x - mu_tier))
```

거리가 작으면 해당 tier가 과거에 성공했던 문제들과 비슷하다는 뜻입니다.

```text
if D_M(x, cheap) <= radius_cheap:
    cheap 가능
elif D_M(x, mid) <= radius_mid:
    mid 가능
else:
    premium
```

이 방식의 장점은 threshold를 단순 감으로 정하지 않아도 된다는 점입니다. 예를 들어
`radius = 2.0`은 “성공 분포에서 대략 몇 표준편차 안쪽인가”라는 통계적 의미를
갖습니다.

물론 radius도 완전히 공짜로 정해지는 값은 아닙니다. 하지만 `lambda`나 임의의
quality threshold보다 검증하기 쉽습니다.

```text
radius 후보 sweep
  -> under-routing 측정
  -> over-routing 측정
  -> budget 초과 측정
  -> tier별 최적 반경 선택
```

## 4. Cheapest-Passing과의 결합

기하학적 라우터는 `Cheapest-Passing Router`를 대체하기보다 보강합니다.

권장 흐름은 다음입니다.

```text
1. evaluator로 pass/fail label 생성
2. 성공 샘플만 골라 tier별 feature 공간 학습
3. 새 프롬프트의 feature 좌표 계산
4. cheap feasibility envelope 확인
5. 가능하면 cheap 선택
6. 불확실하면 P(pass | prompt, model) 확인
7. 그래도 부족하면 mid/premium으로 확장
```

즉 `Cheapest-Passing`은 “통과 확률”을 보고, 기하학적 라우터는 “과거 성공 공간 안에
있는가”를 봅니다. 두 신호가 일치하면 강한 선택 근거가 됩니다.

```text
cheap envelope 안에 있음
cheap pass 확률 높음
=> cheap 선택 근거 강함
```

반대로 둘이 충돌하면 불확실한 케이스로 보고 상위 모델 또는 probe 전략을 사용할 수
있습니다.

```text
cheap envelope 밖에 있음
cheap pass 확률은 높음
=> evaluator 또는 probe로 확인 필요
```

## 5. 구현 MVP

처음부터 복잡한 공간 모델을 만들 필요는 없습니다. MVP는 다음 정도면 충분합니다.

```text
features:
  difficulty_score
  risk_score
  condition_count
  missing_context_flag
  exact_answer_flag
  evaluation_type_id

labels:
  success
  expected_min_model
```

구현 순서:

```text
1. evaluator로 success label 생성
2. expected_min_model 계산
3. 모델별 성공 샘플 feature 평균과 공분산 계산
4. 마할라노비스 거리 계산
5. cheap -> mid -> premium 순서로 feasible 여부 판단
6. budget simulator로 radius 보정
```

공분산 행렬이 불안정할 수 있으므로 초기에는 regularization을 넣습니다.

```text
Sigma_reg = Sigma + epsilon * I
```

샘플이 적은 도메인은 전체 공분산을 공유하고, 샘플이 충분한 도메인만 별도 공간을
학습합니다.

## 6. 도메인별 공간 분리

같은 `difficulty_score`라도 도메인마다 의미가 다를 수 있습니다.

예를 들어 `math`에서 난이도 0.6은 mid로 충분할 수 있지만, `legal`에서 난이도 0.6과
risk 0.8은 clarification 또는 premium 판단이 필요할 수 있습니다.

따라서 다음을 비교해야 합니다.

```text
global envelope:
  모든 도메인 공통 mu, Sigma

domain envelope:
  math, code, legal, business, architecture별 mu, Sigma
```

초기에는 global envelope로 시작하고, 데이터가 쌓이면 benchmark_id 또는 task_type별
공간을 분리합니다.

## 7. 장점과 위험

장점:

- `lambda` 없이 비용-품질 trade-off를 표현할 수 있습니다.
- threshold 하나보다 풍부한 경계를 만들 수 있습니다.
- 기존 difficulty_score를 재활용할 수 있습니다.
- viewer에서 선택 이유를 시각화하기 좋습니다.
- “cheap이 가능한 영역 안에 있는가?”라는 설명이 가능합니다.

위험:

- 데이터가 적으면 mu, Sigma 추정이 불안정합니다.
- feature가 부실하면 공간 모델도 의미가 없습니다.
- rubric_check 도메인은 success label 자체가 흔들릴 수 있습니다.
- radius도 검증 없이 두면 또 다른 placeholder가 됩니다.
- private simulator의 action 비용 구조와 반드시 맞춰봐야 합니다.

## 결론

기하학적 라우터는 기존 `lambda` 기반 utility를 대체할 수 있는 좋은 방향입니다.
특히 다음 세 가지를 결합하면 설득력 있는 새 구조가 됩니다.

```text
파레토 프론티어:
  budget 안에서 도달 가능한 최대 품질을 표현

feasibility envelope:
  각 tier가 성공 가능한 feature 공간을 표현

Cheapest-Passing:
  충분히 통과할 가장 싼 모델을 선택
```

핵심은 라우팅을 스칼라 점수 최적화가 아니라 공간 안의 가능 영역 탐색으로 바꾸는
것입니다.
