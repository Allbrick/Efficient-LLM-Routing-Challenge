# 새로운 LLM Router 아이디어 3가지

이 문서는 기존 `quality_utility_router_baseline`의 단점을 반복하지 않기 위한
초기 설계 아이디어입니다. 세 아이디어는 서로 경쟁하는 대안이라기보다, 하나의
라우터를 구성하는 계층으로 보는 편이 더 정확합니다.

기존 라우터의 핵심 문제는 `quality_score - lambda * cost` 구조였습니다.
`lambda`는 실제 챌린지 예산 시뮬레이션에서 나온 값이라기보다, 품질과 비용을
하나의 점수로 섞기 위한 가정 기반 placeholder에 가까웠습니다.

새 라우터의 목표는 더 좋은 `lambda`를 찾는 것이 아니라, 가능한 한 `lambda`가
필요 없는 구조로 문제를 다시 정의하는 것입니다.

```text
기존 질문:
  어떤 모델의 utility가 가장 높은가?

새 질문:
  이 프롬프트에서 통과해야 할 검증 기준은 무엇이고,
  그 기준을 만족할 수 있는 가장 싼 모델은 무엇인가?
```

다만 주의해야 합니다. `lambda`를 없애더라도 threshold, risk score, rubric이 또
다른 placeholder가 될 수 있습니다. 따라서 새 구조의 핵심은 threshold를 사람이
감으로 정하는 것이 아니라, evaluator 결과와 budget simulator로 계속 보정하는
것입니다.

## 1. Evidence-First Router

프롬프트를 바로 `cheap`, `mid`, `premium`으로 분류하지 않고, 먼저 검증 가능한
근거를 추출하는 방식입니다.

라우터는 프롬프트에서 다음 evidence를 추출합니다.

- 정답이 명확한가?
- 실행 테스트로 검증 가능한가?
- 입력 정보가 부족한가?
- 실패했을 때 위험한가?
- 요구 조건이 몇 개인가?
- 후보 출력 중 이미 통과한 답이 있는가?

이 접근의 장점은 `안녕`, `2 + 3`, `대한민국의 수도` 같은 프롬프트를 단순히
“짧으니까 cheap”으로 처리하지 않는다는 점입니다. 대신 “정답이 명확하고 검증
가능하므로 cheap으로 충분하다”는 근거를 남깁니다.

하지만 evidence extraction 자체가 사람이 만든 heuristic이면 기존의 수동
`prompt_policy.py`와 큰 차이가 없어질 수 있습니다. feature 이름만 바뀌고 실제로는
또 다른 규칙 묶음이 될 수 있습니다.

따라서 evidence는 키워드 규칙보다 평가 가능한 스펙으로 남겨야 합니다.

```text
나쁜 방향:
  법률 키워드가 있으면 위험하다.

좋은 방향:
  계약 본문, 관할, 판단 기준이 없으므로 required_clarification이다.
```

MVP에서는 `example_eval_specs.csv`를 읽어 다음 값을 계산하는 evaluator부터 만들 수
있습니다.

```text
evaluation_type
required_conditions
critical_failure
test_pass_rate
success
expected_min_model
```

Evidence-First Router는 단독 라우터라기보다, 뒤의 Cheapest-Passing Router가 사용할
threshold와 evaluator 종류를 정하는 앞단 계층으로 보는 것이 적절합니다.

## 2. Cheapest-Passing Router

품질 점수를 예측하는 대신, 각 모델이 해당 프롬프트를 통과할 확률을 예측합니다.

기존 방식:

```text
predict quality_score(model)
utility = quality - lambda * cost
```

새 방식:

```text
predict P(pass | prompt, model, tier)
cheap부터 검사해서 pass 확률이 threshold 이상인 첫 모델 선택
```

예를 들어 다음과 같은 예측이 있다면 premium 품질이 조금 더 좋아 보여도 cheap을
선택합니다.

```text
cheap pass 확률   = 0.97
mid pass 확률     = 0.99
premium pass 확률 = 0.99

선택: cheap
```

LLM Router의 목적은 가장 좋아 보이는 모델을 고르는 것이 아니라, 충분히 통과하는
가장 싼 모델을 찾는 것입니다.

budget tier별 threshold는 다르게 둘 수 있습니다.

```text
Fast      threshold = 0.75
Balanced  threshold = 0.85
Premium   threshold = 0.93
```

하지만 이 threshold도 새로운 가정입니다. `lambda` 문제를 threshold 문제로 옮긴
것에 그치지 않으려면, threshold는 반드시 시뮬레이션으로 정해야 합니다.

```text
1. public set에서 evaluator로 pass/fail label 생성
2. 모델별 P(pass | prompt, model) 학습
3. threshold 후보들을 sweep
4. tier별 budget simulator 실행
5. 평균 품질, 예산 초과, 과소 라우팅, 과대 라우팅을 함께 측정
6. tier별 threshold 선택
```

위험도가 높은 프롬프트는 threshold를 올릴 수 있습니다. 단, 이 위험도는 별도
하드코딩이 아니라 Evidence-First 계층에서 나온 `risk_level`, `critical_failure`,
`required_clarification` 같은 근거와 연결되어야 합니다.

이 방식은 `2 + 3`이 mid로 가거나, 간단한 단답 문제가 premium으로 가는 문제를
구조적으로 줄입니다.

## 3. Probe-Then-Escalate Router

한 번에 모델을 고르는 대신, cheap 결과를 먼저 검사하고 부족할 때만 승급하는
방식입니다.

라우팅 흐름은 다음과 같습니다.

```text
1. cheap 호출 또는 기존 cheap output 확인
2. evaluator로 cheap output 검사
3. 통과하면 cheap output 선택
4. 실패하면 mid로 승급
5. mid도 실패하면 premium으로 승급
```

이 방식은 `PROJECT.md`의 입력 구조와 가장 잘 맞습니다.

- 프롬프트
- budget tier
- 호출 이력
- 후보 모델 메타데이터
- 기존 후보 출력 중 최종 답 선택

특히 public 데이터처럼 모든 후보 출력이 이미 주어진 경우에는 evaluator가 후보
출력을 직접 검사할 수 있습니다. 반대로 private simulator에서 선택한 action에
대응하는 결과만 열리는 구조라면, cheap probe 비용이 실제 예산에 누적됩니다.

따라서 이 방식은 반드시 budget simulator와 함께 검증해야 합니다.

핵심 evaluator는 다음과 같습니다.

```text
exact_match      -> 정답 문자열 비교
numeric_check    -> 수치 오차 허용 비교
unit_test        -> 코드 테스트 실행
exact_json       -> 파싱 후 구조 비교
constraint_check -> 조건 충족 여부 검사
rubric_check     -> 필수 개념과 금지 위반 검사
clarification    -> 추가 정보 요청이 맞는지 검사
```

이전 라우터는 prompt만 보고 모델을 고르는 single-shot 구조에 가까웠습니다.
Probe-Then-Escalate는 cheap이 실제로 실패했는지 본 뒤에 승급하므로 챌린지의
history/output 기반 구조와 더 잘 맞습니다.

## 최종 구조 제안

세 아이디어는 다음 순서로 결합하는 것이 좋습니다.

```text
Evidence-First
  -> 검증 가능성, 입력 부족, 위험도, 조건 수 추출
  -> evaluator 종류와 threshold 보정에 사용

Cheapest-Passing
  -> 모델별 pass 확률 예측
  -> 충분히 통과할 가장 싼 모델 선택

Probe-Then-Escalate
  -> 실제 후보 output 또는 호출 이력을 evaluator로 검사
  -> 통과하지 못할 때만 승급
```

1차 MVP는 `Cheapest-Passing Router`가 가장 적절합니다.

이유는 다음입니다.

- 목표가 명확하다: 충분히 통과하는 가장 싼 모델
- 학습 label이 명확하다: pass/fail, expected_min_model
- 기존 단점과 직접 연결된다: quality_score 중심 문제를 줄인다
- viewer에서 설명하기 쉽다: 모델별 pass 확률과 선택 이유를 보여줄 수 있다

다만 Cheapest-Passing만으로는 완결되지 않습니다. threshold 조정에는
Evidence-First가 필요하고, 실제 후보 출력과 history를 활용하려면
Probe-Then-Escalate가 필요합니다.

## 다음 구체화 과제

다음 단계는 evaluator를 domain과 task type별로 매핑하는 것입니다. 특히 `legal`,
`business`, `architecture`처럼 명확한 unit test가 어려운 영역은 `rubric_check`가
필요합니다. 이 rubric을 어떻게 pass/fail로 바꿀지가 가장 중요합니다.

초기 매핑은 다음처럼 둘 수 있습니다.

```text
math_exact        -> exact_match 또는 numeric_check
string_transform  -> exact_match
code              -> unit_test
json_transform    -> exact_json
summary           -> constraint_check
legal_ambiguous   -> clarification
business_analysis -> rubric_check
architecture      -> rubric_check + contradiction_check
```

결국 새 라우터의 핵심은 “어떤 모델이 좋아 보이는가”가 아니라, “이 프롬프트에서
어떤 evaluator를 통과해야 하며, 그 통과를 가장 싸게 달성할 모델은 무엇인가”로
문제를 재정의하는 것입니다.

## 관련 확장 아이디어

- [기하학적 LLM Router 아이디어](geometric-router-ideas.md)

이 확장 문서는 `lambda` 기반 스칼라 utility를 비용-품질 파레토 프론티어,
difficulty-risk 능력 영역, 마할라노비스 거리 기반 feasibility envelope로 대체하는
방향을 다룹니다.
