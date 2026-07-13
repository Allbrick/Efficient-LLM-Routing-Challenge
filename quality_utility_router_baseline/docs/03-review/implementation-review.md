# 구현 평가 보고서

이 문서는 현재 `Efficient-LLM-Routing-Challenge` 프로젝트가 어떻게 구현되어 있는지, 어떤 점이 좋은 설계인지, 어떤 점이 잘못 설계되었는지 냉정하게 평가한다.

평가 기준은 챌린지 목표다.

- 저비용 모델 우선 활용
- 고난도 문제만 상위 모델로 승급
- 불필요한 호출 최소화
- 제한 예산 내 품질 최대화
- 외부 API 없이 로컬 코드로 동작
- Fast / Balanced / Premium budget tier 입력 반영
- 재현 가능한 오픈소스 라우터

## 1. 현재 구현 요약

현재 프로젝트는 크게 네 층으로 구성되어 있다.

```text
data/public/
  example_train.csv
  example_eval_specs.csv
  router_feedback.csv

src/
  feature_extractor.py
  candidate_expander.py
  quality_predictor.py
  calibrator.py
  utility_engine.py
  prompt_policy.py
  router.py

training/
  01_data_validation.py
  02_oracle_analysis.py
  03_train_oof.py
  04_calibration.py
  05_lambda_optimize.py
  06_final_build.py
  07_feedback_tune.py

viewer/
  index.html
  app.js
  styles.css
  router_eval.json
  router_eval.js
```

런타임 라우팅은 다음 순서로 동작한다.

```text
prompt + budget_tier + candidate_models
        |
        v
FeatureExtractor
        |
        v
CandidateExpander
        |
        v
LightGBM QualityPredictor
        |
        v
Calibrator
        |
        v
PromptPolicy prior
        |
        v
UtilityEngine
        |
        v
selected model_id
```

핵심 점수식은 다음이다.

```text
utility(model) = policy_adjusted_quality(model) - lambda(tier) * normalized_cost(model)
```

`lambda`는 tier별 비용 민감도다.

```text
fast >= balanced >= premium >= 0
```

## 2. 잘 만들어진 점

### 2.1 컴포넌트 경계가 비교적 명확하다

`src/` 모듈이 책임별로 분리되어 있다.

- `FeatureExtractor`: 프롬프트를 수치 feature로 변환
- `CandidateExpander`: 후보 모델별 행으로 확장
- `QualityPredictor`: 모델별 예상 품질 예측
- `Calibrator`: 모델별 예측 bias 보정
- `UtilityEngine`: 품질-비용 tradeoff로 최종 선택
- `Router`: 전체 오케스트레이션

이 구조는 좋다. 특히 predictor와 utility decision을 분리한 것은 중요하다. 품질 예측 모델은 tier를 몰라도 되고, tier별 정책은 utility layer에서 반영할 수 있다.

### 2.2 외부 모델/API 호출 없이 로컬에서 동작한다

챌린지 규칙상 외부 API, 네트워크 서비스, 실시간 LLM 호출이 금지된다. 현재 구현은 LightGBM, sklearn, numpy, pandas 기반 로컬 artifact로 동작한다.

이 점은 문제 조건에 잘 맞는다.

### 2.3 long-format 학습 데이터 구조는 적절하다

현재 `example_train.csv`는 다음 형태다.

```csv
prompt_id,prompt,domain,task_type,benchmark_id,model_id,model_output,quality_score,cost
```

한 프롬프트당 `cheap`, `mid`, `premium` 행이 모두 존재한다. 이 구조는 후보 모델별 품질 예측을 학습하기에 적합하다.

```text
prompt_id = e001
  cheap output + quality + cost
  mid output + quality + cost
  premium output + quality + cost
```

라우터 문제를 “프롬프트 하나를 분류”하는 문제가 아니라 “프롬프트-모델 쌍의 품질 예측” 문제로 만든 것은 좋은 방향이다.

### 2.4 OOF 기반 calibration을 둔 것은 좋은 판단이다

모델별 raw prediction은 직접 비교하면 편향이 생길 수 있다.

예:

```text
cheap 예측은 항상 낮게 나옴
premium 예측은 항상 높게 나옴
```

`Calibrator`가 OOF prediction 기반으로 모델별 bias를 보정하는 구조는 필요하다. 실제 라우팅에서는 모델 간 상대 비교가 핵심이므로 calibration은 선택 정확도에 직접 영향을 준다.

### 2.5 feedback regression loop를 만든 것은 매우 좋다

최근 추가된 구조:

```text
data/public/router_feedback.csv
training/07_feedback_tune.py
tests/test_feedback_cases.py
```

이 구조는 프로젝트의 방향을 크게 개선한다.

이전에는 잘못된 라우팅이 나오면 `prompt_policy.py`를 직접 수정했다. 이것은 유지보수하기 어렵고 주관적이다.

이제는 사용자가 정답 라우팅을 준 케이스를 feedback dataset에 저장하고, 회귀 테스트로 고정할 수 있다.

예:

```csv
f001,"2 + 3의 값만 숫자로 답해줘.",balanced,cheap,exact_match,"5",exact_answer
f008,"다음 코드를 고쳐줘.",balanced,premium,required_clarification,,missing_context
```

이 방식은 “라우터가 다시 같은 실수를 하지 않게 하는 최소 안전망”이다.

### 2.6 example_eval_specs.csv를 분리한 것은 방향이 좋다

`example_train.csv`는 현재 학습 파이프라인 호환을 위해 `quality_score`를 유지한다.

하지만 `example_eval_specs.csv`에는 다음 정보가 들어간다.

```csv
prompt_id,prompt,task_type,difficulty,risk_level,expected_min_model,evaluation_type,reference_answer,test_spec
```

이 분리는 좋다. 장기적으로는 `quality_score`를 사람이 매기는 방식이 아니라 evaluator가 자동 계산해야 한다.

예:

```text
exact_match
unit_test
exact_json
constraint_check
rubric_check
required_clarification
```

이 방향은 챌린지 라우터 평가에 더 적합하다.

### 2.7 viewer는 디버깅 도구로 유용하다

viewer는 다음 정보를 보여준다.

- prompt
- tier
- 선택 모델
- 후보별 predicted quality
- calibrated quality
- policy quality
- cost
- utility

이 정보가 없으면 왜 특정 모델이 선택됐는지 알기 어렵다. 라우터는 디버깅이 어려운 시스템이므로, viewer는 매우 유용하다.

특히 잘못된 라우팅을 발견하는 데 직접 도움이 되었다.

예:

```text
"안녕" -> premium
"2 + 3..." -> mid
"다음 코드를 고쳐줘." -> cheap
```

이런 케이스는 viewer가 없으면 발견하기 어렵다.

## 3. 잘못 설계된 점

### 3.1 prompt_policy.py가 너무 많은 책임을 떠안고 있다

현재 가장 큰 구조적 문제는 `prompt_policy.py`다.

초기에는 `SIMPLE_MARKERS`, `COMPLEX_MARKERS` 같은 키워드 하드코딩이 있었다. 이후 제거했지만, 지금도 구조적 prior와 특수 케이스 처리가 꽤 많이 들어 있다.

현재 들어간 개념:

- 구조 기반 complexity
- ultra simple prompt 판단
- missing context 판단
- exact answer 판단
- tier별 prior adjustment

이 파일은 사실상 “학습 모델의 약점을 보정하는 수동 정책 엔진”이 되었다.

이것은 단기적으로는 효과가 있지만, 장기적으로는 위험하다.

문제:

- 정책이 점점 복잡해진다.
- 새 예외가 나올 때마다 코드가 늘어난다.
- 학습 모델과 정책 prior의 책임 경계가 흐려진다.
- 실제 private dataset에서 일반화될지 알 수 없다.

특히 다음 로직은 위험하다.

```text
exact_answer_signal
missing_context_signal
ultra_simple
```

이들은 모두 필요한 개념이지만, 코드 규칙으로 계속 키우기보다 학습 데이터와 evaluator로 흡수해야 한다.

### 3.2 현재 LightGBM 모델이 prompt별 난이도를 충분히 배우지 못한다

여러 번 관찰된 문제다.

초기 모델은 다음처럼 동작했다.

```text
cheap calibrated quality   낮음
mid calibrated quality     높음
premium calibrated quality 더 높음
```

이 차이가 프롬프트별로 크게 달라지지 않았다.

즉 모델이 실제로는:

```text
이 프롬프트는 cheap으로 충분함
이 프롬프트는 mid 필요
이 프롬프트는 premium 필요
```

를 잘 배우지 못하고, 주로 `model_id` 평균 품질 차이를 학습했다.

이것은 라우터에서 치명적이다. 라우터의 핵심은 “프롬프트별로 충분한 최소 모델을 찾는 것”이기 때문이다.

원인:

- 데이터가 작다.
- prompt feature가 충분히 강하지 않다.
- `quality_score`가 원래 주관 점수 중심이었다.
- cheapest-sufficient label이 직접 학습되지 않는다.
- 모델별 output quality gap이 데이터에서 과하게 일정할 수 있다.

### 3.3 quality_score 중심 학습은 목표와 완전히 일치하지 않는다

현재 학습 모델은 기본적으로 `quality_score`를 예측한다.

하지만 라우터가 진짜 알아야 하는 것은 이것이다.

```text
이 모델이 이 프롬프트에서 required threshold를 넘는가?
```

즉 회귀 문제보다 다음이 더 직접적이다.

```text
success(prompt, model, tier) = true / false
expected_min_model(prompt) = cheapest successful model
```

현재 `quality_score` 예측 후 utility로 선택하는 방식은 간접적이다.

이 방식의 문제:

- premium quality가 항상 조금 높으면 premium으로 쏠린다.
- lambda를 높이면 전체가 cheap/mid로 한꺼번에 쏠린다.
- exact-answer task에서 premium의 긴 답변이 오히려 실패인 것을 모델이 안정적으로 배우기 어렵다.

장기적으로는 `quality_score` 회귀뿐 아니라 성공 여부 분류 또는 expected_min_model 학습이 필요하다.

### 3.4 lambda 최적화 objective가 아직 임시적이다

`training/05_lambda_optimize.py`는 개선되었다. 이전에는 quality-only에 가까웠고, 지금은 비용 패널티를 포함한다.

현재 개념:

```text
score = actual_quality - tier_cost_weight * normalized_cost
```

하지만 이 역시 임시 objective다.

챌린지 평가 방식은 다음에 가깝다.

```text
각 tier에서 예산 내 평균 품질
저예산 tier 가중치 높음
품질-비용 tradeoff
```

현재 objective의 문제:

- 실제 예산 constraint를 직접 모델링하지 않는다.
- tier별 budget exhaustion이 없다.
- action history가 없다.
- call_model vs select_output 의사결정을 평가하지 않는다.
- private simulator의 scoring과 다를 가능성이 높다.

따라서 lambda 최적화는 아직 대회 평가식의 근사일 뿐이다.

### 3.5 abstain을 premium으로 대체하고 있다

사용자가 제안한 데이터에는 `abstain` 개념이 있었다.

```text
어느 모델도 바로 답하면 안 되고 거절 또는 추가 정보 요청이 정답
```

하지만 현재 라우터 출력은 `cheap`, `mid`, `premium` 중 하나다.

그래서 `abstain_case`를 실제로는 premium 정답처럼 넣었다.

예:

```text
"이 계약이 법적으로 유효한지 판단해줘."
expected_min_model = premium
```

이것은 정확하지 않다.

진짜 정답은 “premium 모델 호출”이 아니라:

```text
추가 정보를 요청하는 출력 선택
```

또는 challenge action 관점에서는:

```text
이미 후보 출력 중 clarification/refusal output을 선택
```

이어야 한다.

현재 구조는 abstain을 모델 선택 문제로만 흡수하고 있어, 안전/정보 부족 문제를 정확히 모델링하지 못한다.

### 3.6 history 처리가 실제 챌린지보다 단순하다

`router.py`에는 history가 있으면 이미 호출된 모델 중 선택하는 분기가 있다.

하지만 현재 구현은 다음을 충분히 다루지 않는다.

- 여러 단계 호출 전략
- cheap 먼저 호출 후 품질 불충분하면 escalation
- 이미 호출된 output의 실제 내용 기반 선택
- 후보 출력 품질을 추정하는 output-level feature
- budget remaining 상태

챌린지 설명상 입력에는 호출 이력이 포함된다. 현재 구현은 거의 single-shot model selection에 가깝다.

즉 지금 라우터는:

```text
어떤 모델을 부를까?
```

에는 답하지만,

```text
이미 cheap을 불렀는데 충분한가?
추가로 mid/premium을 부를까?
기존 output 중 무엇을 최종 선택할까?
```

에는 아직 약하다.

### 3.7 viewer와 API는 디버깅용이지 평가용이 아니다

viewer는 유용하지만 현재 평가 시스템은 아니다.

한계:

- 직접 입력 프롬프트는 실제 ground truth가 없다.
- viewer의 선택 결과가 맞는지 자동 판정하지 않는다.
- 사용자가 “이건 틀렸다”고 해야 feedback으로 들어간다.
- API 서버는 로컬 디버깅용이며 production 구조는 아니다.

viewer는 “라우터 설명 도구”이지 “성능 검증 도구”가 아니다.

### 3.8 generated viewer data가 repo에 남아 있다

`viewer/router_eval.json`, `viewer/router_eval.js`는 생성물이다. 현재 작업트리에는 이 파일들이 있다.

이 파일들은 크기도 크고, 데이터가 바뀔 때마다 갱신된다.

장기적으로는 다음 중 하나가 낫다.

- `viewer/router_eval.*`를 gitignore
- 필요 시 build script로 생성
- small demo snapshot만 별도 보관

현재는 편의상 남겨두었지만, 재현성 관리 관점에서는 생성물과 소스가 섞여 있다.

## 4. 현재 데이터 설계 평가

### 4.1 좋아진 점

초기 데이터는 사람이 임의로 `0.92`, `0.95` 같은 점수를 넣는 형태였다. 지금은 일부 샘플에서 다음 식으로 바뀌었다.

```text
exact_match
unit_test
exact_json
constraint_check
rubric_check
required_clarification
```

이 방향은 옳다.

특히 다음 샘플들은 라우터 학습에 좋다.

- `e001`: 산술 exact answer
- `e006`: 단순 add 함수 unit test
- `e101`: 예외 처리와 반복문 조건이 있는 fibonacci
- `e103`: JSON 타입 검증
- `e201`: 결제 시스템 복합 설계
- `e202`: WebSocket 분산 시스템 보장 설계
- `e203`: TypeScript 제한 동시성 실행기
- `e401`~`e404`: 길이와 난이도 대조쌍

이 데이터들은 “premium이 멋있어 보인다”가 아니라, “어떤 조건을 통과했는가”로 품질을 정의하려는 시도다.

### 4.2 여전히 부족한 점

현재 `example_train.csv`는 54 prompts / 162 rows다.

규모가 작다. 특히 새로 추가된 객관 평가형 샘플은 아직 소수다.

분포도 균형적이지 않다.

```text
cheap_exact             5
cheap_code              1
mid_code                1
mid_summary             1
mid_transform           1
premium_architecture    1
premium_distributed     1
premium_code            1
abstain_case            2
contrast_pair           4
```

이 정도 데이터로는 모델이 일반화하기 어렵다. 그래서 `prompt_policy.py`가 많은 보정을 떠안고 있다.

## 5. 테스트 설계 평가

### 5.1 좋은 점

현재 테스트 수는 39개이며 다음을 검증한다.

- feature extractor
- candidate expander
- calibrator
- utility engine
- router 흐름
- feedback cases

특히 `tests/test_feedback_cases.py`는 좋은 추가다.

사용자가 직접 정답을 준 케이스가 다시 깨지지 않도록 막는다.

### 5.2 부족한 점

아직 테스트가 다음을 충분히 검증하지 않는다.

- 전체 training pipeline end-to-end
- generated artifacts schema
- viewer API `/api/route`
- `prompt_policy.py`의 주요 경계 조건
- exact answer / missing context / hard prompt routing
- expected_min_model 기반 손실 함수

지금은 테스트가 “코드가 실행된다”는 보장에 가깝고, “라우터가 대회 목표를 잘 달성한다”는 보장은 약하다.

## 6. 가장 위험한 설계 리스크

### 리스크 1: 수동 prior가 계속 커질 수 있다

현재 잘못된 라우팅을 발견할 때마다 policy rule을 고쳤다.

예:

- 안녕
- 2 + 3
- 대한민국 수도
- 다음 코드를 고쳐줘
- Fast에서도 premium 필요

이 접근은 빠르게 효과가 있지만, 계속하면 규칙 덩어리가 된다.

궁극적으로는 이 규칙들이 데이터와 학습으로 흡수되어야 한다.

### 리스크 2: private set에서 분포가 바뀌면 성능이 흔들릴 수 있다

현재 feature와 policy는 example data에 맞춰 튜닝됐다. private set에서 다음이 달라지면 성능이 크게 흔들릴 수 있다.

- 모델 이름
- cost scale
- prompt length distribution
- task type distribution
- exact answer 비율
- safety/clarification 케이스 비율

### 리스크 3: model output을 거의 사용하지 않는다

챌린지에는 후보 모델 출력과 history가 있다. 현재 라우터는 mostly prompt-level model selection이다.

하지만 실제로는 cheap output이 이미 충분한지 판단하는 것이 중요할 수 있다.

예:

```text
cheap output이 exact_match를 만족하면 더 호출할 필요 없음
cheap output이 조건을 빠뜨렸으면 escalate
```

현재는 output-level evaluator가 런타임 decision에 거의 들어가지 않는다.

## 7. 개선 우선순위

### P0: expected_min_model 기반 evaluator 구현

가장 먼저 해야 한다.

`example_eval_specs.csv`를 읽어서 각 `model_output`을 평가하고 다음을 자동 산출해야 한다.

```text
passed_required_conditions
total_required_conditions
critical_failure
test_pass_rate
success
expected_min_model
```

그리고 `quality_score`는 수동 입력이 아니라 이 결과에서 생성되어야 한다.

### P1: success classifier 추가

`quality_score` 회귀만으로는 부족하다.

추가로 다음을 학습해야 한다.

```text
P(success | prompt, model)
```

라우팅은 다음처럼 바꿀 수 있다.

```text
eligible_models = models where P(success) >= threshold(tier)
select cheapest eligible model
```

이 방식이 라우터 목표와 더 직접적으로 맞다.

### P2: prompt_policy.py 축소

현재 policy prior는 임시 보정이다.

목표:

- exact answer
- missing context
- hard prompt

같은 개념을 수동 rule에서 evaluator label / classifier feature로 이동시킨다.

최종적으로 `prompt_policy.py`는 작아져야 한다.

### P3: history/output-aware routing 구현

현재 구조는 single-shot에 가깝다.

다음 로직이 필요하다.

```text
if no history:
    choose initial model
else:
    evaluate existing outputs
    if sufficient:
        select_output
    else:
        call next model
```

이를 위해 output evaluator가 필요하다.

### P4: budget simulator 구현

현재 lambda는 단일 요청 기준 비용 패널티다.

대회 목표는 tier별 예산 내 평균 품질이다. 따라서 다음이 필요하다.

```text
simulate N prompts under tier budget
track total cost
track average quality
penalize budget overflow
```

현재 lambda 최적화보다 이쪽이 더 실제 평가에 가깝다.

### P5: generated artifact 정리

`viewer/router_eval.json`, `viewer/router_eval.js`, `artifacts/*`는 생성물이다.

권장:

```text
source: scripts, src, training, tests, docs, data small samples
generated: artifacts, viewer/router_eval.*
```

생성물은 재현 가능한 명령으로 만들고, 필요 시 gitignore하는 편이 낫다.

## 8. 최종 평가

현재 프로젝트는 “라우터 MVP”로는 꽤 잘 만들어졌다.

좋은 점:

- 로컬 artifact 기반으로 동작한다.
- 학습/보정/utility 구조가 분리되어 있다.
- viewer로 디버깅 가능하다.
- feedback regression loop가 생겼다.
- objective가 quality-only에서 비용-aware로 개선되었다.
- 데이터가 주관 점수에서 객관 평가 스펙 중심으로 이동하고 있다.

하지만 아직 “대회에서 강한 라우터”라고 보기는 어렵다.

핵심 약점:

- 학습 모델이 prompt별 최소 충분 모델을 충분히 배우지 못한다.
- 수동 policy prior가 성능을 많이 떠받치고 있다.
- abstain/history/output selection이 약하다.
- 실제 budget simulator가 없다.
- `quality_score` 회귀가 챌린지 목표와 완전히 일치하지 않는다.

따라서 현재 상태를 한 문장으로 평가하면 다음과 같다.

```text
구조는 올바른 방향으로 잡혔지만, 실제 라우팅 지능은 아직 학습 모델보다 수동 prior와 피드백 회귀 테스트에 많이 의존하는 MVP 단계다.
```

가장 중요한 다음 단계는 규칙을 더 늘리는 것이 아니라, `example_eval_specs.csv` 기반 evaluator를 만들어 `expected_min_model`과 `success`를 자동 계산하고, 이를 직접 학습하는 구조로 바꾸는 것이다.

