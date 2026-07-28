# Efficient LLM Routing Challenge 고도화 Plan

## 1. 목표

이 문서는 `PROJECT.md`의 대회 과제 목표와 2026 오픈소스 개발자대회 결과보고서 양식을 기준으로, 심사관이 기대하는 방향과 현재 코드의 부족한 점을 연결해 프로젝트 고도화 실행 계획을 정리한다.

최종 목표는 단순히 라우터가 동작하는 수준을 넘어서, 다음을 결과보고서 5페이지 안에서 설득 가능한 오픈소스 출품작으로 만드는 것이다.

- Fast/Balanced 저예산 tier에서 비용을 강하게 절감하면서 품질 저하를 통제한다.
- 외부 API 없이 로컬 코드만으로 재현 가능한 라우팅 정책을 제공한다.
- `prompt`, `budget_tier`, `history`, `model_metadata`를 모두 활용하는 private simulator 친화 인터페이스를 완성한다.
- 성능 근거, 재현 명령, 시연 영상, SBOM, AI 모델 활용 정보를 명확히 제출할 수 있게 정리한다.

## 2. 심사관이 보고 판단할 가능성이 높은 기준

### 2.1 결과보고서 관점

대회 접수 양식상 심사관은 코드 저장소만 보는 것이 아니라 결과보고서에서 다음을 빠르게 확인한다.

- 프로젝트 개요: 무엇을 해결하는 프로젝트인지 1~2줄로 명확한가.
- 개발배경 및 목적: LLM 비용 낭비 문제와 라우팅 필요성이 설득력 있게 설명되는가.
- 개발환경: OS, Python 버전, 주요 라이브러리, 로컬 AI 실행 방식이 재현 가능한가.
- 시스템 구성 및 아키텍처: `viewer -> router -> ai` 흐름, simulator adapter, 데이터/학습/평가 흐름이 그림 없이도 이해되는가.
- 주요기능: 라우팅, budget tier, abstain, evaluator, viewer, batch simulator가 어떤 기능인지 분명한가.
- 구동 및 시연: 설치부터 테스트, 라우터 실행, viewer 실행, 평가 명령까지 따라 할 수 있는가.
- 기대효과: LLM 운영 비용 절감, 온디바이스/사내망/교육용 라우팅 등 활용처가 구체적인가.
- 혁신성 및 차별성: 단순 키워드 라우터가 아니라 evaluator 기반 success 라벨, budget-aware allocation, local-only routing이라는 차별점이 있는가.
- 한계점 및 로드맵: 현재 약점을 숨기지 않고, 개선 계획이 기술적으로 타당한가.
- 소감 및 후기: 기술적 시행착오와 문제 해결 과정이 자연스럽게 드러나는가.

### 2.2 기술 심사 관점

`PROJECT.md`의 평가 방향을 보면 실제 기술 심사는 다음 항목에 집중될 가능성이 높다.

- Fast tier에서 premium 호출을 얼마나 억제하는가.
- Budget constraint를 위반하지 않으면서 평균 품질을 얼마나 유지하는가.
- 쉬운 문제를 cheap으로 보내는 능력과 어려운 문제를 premium으로 올리는 능력이 균형적인가.
- `history`가 있을 때 기존 출력 선택과 추가 호출 판단을 할 수 있는가.
- `model_metadata`의 실제 비용 정보를 사용해 모델 이름이나 cost scale이 바뀌어도 동작하는가.
- 라우터가 답변을 직접 생성하지 않고 후보 모델 호출/선택 action만 반환하는가.
- 외부 API, 네트워크 호출 없이 로컬 코드로만 동작하는가.
- 공개 데이터에 과적합된 하드코딩이 아니라 private set에도 일반화될 구조인가.
- 코드, 테스트, 문서, 라이선스가 오픈소스 프로젝트로 제출 가능한 상태인가.

## 3. 현재 프로젝트의 강점

### 3.1 구조적 강점

- 공통 실행 스택이 `viewer -> router -> ai`로 분리되어 있다.
- 제출 후보인 `router_impls/geometric/`가 별도 구현체로 정리되어 있다.
- `submission.py`가 private simulator adapter 역할을 한다.
- `cheap`, `mid`, `premium`, `abstain` 선택 구조가 이미 존재한다.
- viewer와 router server가 있어 시연 영상 제작이 쉽다.
- 테스트가 존재하고, `router_impls/geometric/tests` 기준 통과한다.

### 3.2 알고리즘 강점

- 단순 품질 회귀가 아니라 `success`, `expected_min_model`, pass probability, sufficiency risk를 사용하려는 방향이 좋다.
- `OutputEvaluator`가 `exact_match`, `numeric_check`, `unit_test`, `exact_json`, `constraint_check`, `rubric_check`, `required_clarification`, `refusal_check`를 지원한다.
- `abstain`을 모델 선택 후보로 다루는 구조가 있어 정보 부족/거절 케이스를 확장하기 쉽다.
- `budget_allocator.py`가 batch budget allocation을 구현하고 있어 tier별 총예산 평가로 발전시킬 기반이 있다.

### 3.3 결과보고서에서 강조할 차별점

- 외부 LLM API를 호출하지 않는 로컬 라우터다.
- 모델 출력 품질 평가를 사람이 임의 점수로만 넣지 않고, 평가 스펙 기반 pass/fail로 전환하려고 한다.
- budget tier별로 다른 라우팅 정책을 적용한다.
- viewer를 통해 라우터의 선택 이유와 후보별 진단 정보를 확인할 수 있다.
- 비용 절감형 AI 운영을 위한 오픈소스 reference architecture로 확장 가능하다.
- geometric 을 활용
- 검증된 공개 AI 모델과 공개 데이터셋을 활용하되, 최종 라우팅 정책은 자체 구현한다.
- RouteLLM/LMSYS 계열 선호 데이터와 한국어 instruction 데이터를 라우팅 평가 포맷으로 변환해 활용할 수 있다.
- 경량 임베딩 모델을 feature extractor로 활용하면 단순 규칙 기반 라우터보다 일반화 가능성을 높일 수 있다.

## 4. 현재 코드의 핵심 부족점

### 4.1 Fast/Balanced 비용 제어가 약함

현재 `artifacts/geometric_simulation.json` 기준 일반 라우팅은 품질은 높지만 비용 초과가 심하다.

- Fast: budget limit `0.03`, mean cost `0.128`, cost over limit `50/73`
- Balanced: budget limit `0.08`, mean cost `0.135`, cost over limit `48/73`
- Premium 선택 비중이 높아 저예산 tier의 핵심 평가 포인트와 충돌한다.

반대로 `artifacts/geometric_allocation.json`의 batch allocation은 총예산은 맞추지만 under-route가 늘어난다.

- Fast batch allocation: total budget `2.19`, total cost `2.19`
- mean quality `0.878`
- under_route `20/73`

즉 현재 라우터는 "품질을 위해 비싸게 쓰는 모드"와 "예산을 맞추지만 어려운 문제를 놓치는 모드" 사이의 균형점이 부족하다.

### 4.2 `history`와 `model_metadata`를 버림

`router_impls/geometric/submission.py`에서 `history`와 `model_metadata`를 `del`로 버린다. 이는 private simulator 입력 정의와 맞지 않는다.

문제점:

- 이미 호출된 cheap/mid/premium output 중 충분한 답변이 있는지 판단하지 못한다.
- 이미 비용을 지불한 output을 재사용하지 못한다.
- 후보 모델의 실제 비용과 metadata가 바뀌어도 내부 평균 cost에 의존한다.
- `call_model`과 `select_output`을 모두 다뤄야 하는 대회 구조에 비해 single-shot model selection에 가깝다.

### 4.3 예산 제약이 runtime decision에 약하게 연결됨

`BUDGET_LIMITS`와 `frontier_hint`는 존재하지만, 실제 `route()`는 개별 요청에서 budget을 강하게 만족시키지 않는다.

문제점:

- Fast에서 budget limit보다 비싼 premium을 자주 선택한다.
- `best_under_budget()`의 결과가 진단 정보에 가까워 실제 선택 제약으로 작동하지 않는다.
- batch allocator와 online router의 정책이 분리되어 있어 제출 시 어떤 정책이 최종인지 애매하다.

### 4.4 private set 일반화 위험

현재 feature는 구조적 feature와 일부 한국어/영어 hint에 의존한다.

위험 요소:

- public data의 task 분포에 맞춘 수동 feature가 private set에서 흔들릴 수 있다.
- synthetic data가 실제 private distribution과 다르면 threshold가 왜곡될 수 있다.
- `simple_prompt_prior`, missing context, exact answer 판단이 규칙 기반이라 edge case에 취약하다.

### 4.5 결과보고서 제출 준비 미흡

현재 저장소에는 `LICENSE` 파일이 없다.

결과보고서 붙임 관점의 부족점:

- SBOM 작성용 라이브러리별 라이선스 표가 없다.
- AI 모델 활용 유형 정리가 없다.
- 직접 작성 코드의 오픈소스 라이선스가 명시되어 있지 않다.
- 시연 영상 스크립트와 결과보고서용 5페이지 구성안이 없다.
- 제출 파일명, PDF 변환, 회색 가이드 문구 삭제 등 문서 제출 체크리스트가 없다.

### 4.6 공개 AI/데이터셋 활용 전략이 아직 약함

현재 프로젝트는 내부 예제 데이터와 자체 synthetic/public-style 데이터 중심으로 구성되어 있다. 이 방향은 안전하지만, 심사관이 보기에는 "실제 공개 AI 생태계와 데이터를 얼마나 잘 활용했는가"라는 측면이 약하게 보일 수 있다.

문제점:

- 라우팅 문제와 직접 연결되는 공개 선호 데이터 활용 근거가 부족하다.
- 한국어 프롬프트 다양성을 뒷받침할 공개 데이터셋 활용 계획이 부족하다.
- prompt similarity, semantic difficulty, task clustering을 위한 경량 AI 모델 활용이 없다.
- 붙임2에서 "AI 모델 활용 정보"를 작성할 때 프로젝트의 AI 활용성이 약해 보일 수 있다.

개선 방향:

- 대형 LLM 파인튜닝은 피한다. 라우터 프로젝트의 초점이 흐려지고 붙임2 부담이 커진다.
- 대신 검증된 공개 데이터셋을 라우팅 학습/평가 데이터로 변환한다.
- 경량 오픈소스 임베딩 모델을 feature extractor로 사용해 prompt similarity와 task difficulty feature를 강화한다.
- 최종 라우팅 정책은 여전히 자체 구현으로 유지해 프로젝트의 독창성을 보존한다.

## 5. 고도화 원칙

### 5.1 대회 점수를 올리는 방향

가장 중요한 개선 방향은 "더 똑똑한 premium 선택"이 아니라 "Fast/Balanced에서 cheap/mid를 안전하게 쓰는 능력"이다.

우선순위:

1. Fast tier premium 과다 선택을 줄인다.
2. cheap으로 충분한 문제를 정확히 cheap으로 보낸다.
3. premium이 꼭 필요한 문제의 under-route를 줄인다.
4. history가 있으면 기존 output을 평가해 추가 호출을 피한다.
5. model_metadata 기반으로 비용 scale 변화에 대응한다.

### 5.2 결과보고서 설득 방향

보고서에서는 완벽한 성능보다 다음 메시지가 중요하다.

- 문제 정의가 명확하다: LLM 비용 낭비를 줄이는 로컬 라우터.
- 오픈소스성이 명확하다: 외부 API 없이 재현 가능한 코드와 문서.
- 실험 근거가 있다: tier별 비용/품질, under-route/over-route, latency, 선택 분포.
- 한계를 인정한다: 작은 데이터, history/output-aware routing 미완성, private 일반화 위험.
- 로드맵이 구체적이다: evaluator 강화, budget-aware policy 통합, simulator adapter 완성.

## 6. 실행 Roadmap

## Phase 0. 제출 기반 정리

목표: 결과보고서 필수 제출 요건을 만족하는 오픈소스 프로젝트 형태를 만든다.

작업:

- `LICENSE` 파일 추가
  - 권장: MIT 또는 Apache License 2.0
  - AI/라우팅 연구 코드의 재사용성을 강조하려면 Apache License 2.0이 더 명확하다.
- `docs/SBOM.md` 작성
  - `pandas`, `numpy`, `pytest`, `lightgbm`, `scikit-learn`, `joblib` 포함
  - 라이브러리명, 버전, 라이선스, 공식 URL, 사용 목적 정리
- `docs/AI_MODEL_USAGE.md` 작성
  - 라우터 자체는 LLM 가중치를 학습한 모델이 아니라 local routing policy임을 명시
  - Ollama 모델은 선택적 시연용이며, 제출 라우터는 외부 API 없이 동작한다고 설명
  - 상용 AI 보조도구를 사용했다면 활용 범위를 별도 기재
- `docs/REPORT_OUTLINE.md` 작성
  - 결과보고서 5페이지 이내 구성안
  - 표/그림으로 넣을 내용과 제외할 내용을 정리
- `docs/DEMO_SCRIPT.md` 작성
  - 시연 영상 3~5분 스크립트
  - viewer 실행, prompt 입력, tier 변경, 라우팅 결과 비교, 평가 명령 순서 포함

완료 기준:

- 결과보고서 붙임1, 붙임2에 들어갈 원천 정보가 저장소에 존재한다.
- README에서 라이선스, SBOM, AI 모델 활용 명세로 연결된다.

예상 점수 효과:

- 오픈소스 제출 적합성 상승
- 심사관 신뢰도 상승
- 감점 방지 효과가 크다.

## Phase 1. Online router와 budget allocator 통합

목표: Fast/Balanced에서 budget limit를 실제 선택 로직에 반영한다.

현재 문제:

- `route()`는 premium을 쉽게 선택한다.
- batch allocator는 별도 도구라 private simulator adapter에 직접 반영되지 않는다.

개선 방향:

- `route()` 안에 tier별 hard budget guard를 추가한다.
  - Fast: 기본적으로 `premium` 선택 금지
  - 단, high-risk/hard/rubric/unit_test에서 premium 필요 확률이 특정 threshold 이상이면 예외 허용
  - Balanced: premium 허용 조건을 Fast보다 완화
  - Premium: 품질 중심 허용
- `frontier_hint`를 진단 정보가 아니라 후보 필터링에 사용한다.
- `cost <= budget_limit` 후보를 우선 선택하고, 예산 초과 후보는 risk override가 있을 때만 선택한다.
- `budget_allocator.py`의 scoring 함수를 `router.py`의 online scoring과 공유한다.
  - 별도 정책이 두 개 존재하지 않게 한다.

구현 후보:

```text
eligible = candidates where cost <= BUDGET_LIMITS[tier]
if high_risk_override:
    allow next model above budget
select cheapest candidate with pass_probability >= threshold
else select best expected utility among eligible
```

추가해야 할 테스트:

- Fast에서 trivial/exact/numeric prompt는 cheap 선택
- Fast에서 medium prompt는 mid 이하 선택
- Fast에서 high-risk hard prompt만 premium 예외 허용
- Balanced에서 premium 과다 선택 방지
- Premium에서 품질 중심 선택 유지

완료 기준:

- public simulation Fast cost_over_limit를 50/73에서 10/73 이하로 낮춘다.
- Fast mean_quality를 0.90 이상으로 유지한다.
- Fast under_route를 10/73 이하로 통제한다.
- Balanced cost_over_limit를 48/73에서 15/73 이하로 낮춘다.

예상 점수 효과:

- 대회 핵심 평가인 저예산 tier 점수가 가장 크게 오른다.

## Phase 2. `history` 기반 select_output 구현

목표: 이미 호출된 모델 출력이 있을 때 추가 호출 없이 기존 output을 선택할 수 있게 한다.

현재 문제:

- `submission.py`가 `history`를 버린다.
- 라우터는 single-shot `call_model` 중심이다.

개선 방향:

- `history` schema를 프로젝트 내부 표준으로 정의한다.
  - `model_id`
  - `output`
  - `cost`
  - `latency_ms`
  - `call_index`
- `OutputEvaluator`를 runtime에도 사용할 수 있게 만든다.
- `history`에 output이 있으면 다음 순서로 판단한다.
  - 현재 prompt와 spec/metadata로 evaluation hint를 만든다.
  - 기존 output 중 success probability가 충분한 것이 있으면 `select_output` 반환
  - 충분하지 않으면 다음 cheapest escalation model을 `call_model`로 반환
- private simulator가 `select_output` 형식을 요구할 수 있으므로 adapter action format을 확장한다.

권장 action 형식:

```python
{"type": "select_output", "model_id": "cheap", "history_index": 0}
{"type": "call_model", "model_id": "mid"}
{"type": "abstain", "model_id": None}
```

추가해야 할 테스트:

- cheap history가 exact_match를 만족하면 select_output
- cheap history가 실패하고 mid 미호출이면 call_model mid
- mid history가 충분하면 premium 호출하지 않음
- required_clarification/refusal output이 있으면 abstain 또는 select_output
- history가 비어 있으면 기존 initial routing 유지

완료 기준:

- `submission.py`에서 `history`를 더 이상 버리지 않는다.
- 기존 output 재사용으로 평균 비용이 낮아진다.
- 결과보고서에 "불필요한 중복 호출 최소화"를 실제 기능으로 설명할 수 있다.

예상 점수 효과:

- PROJECT.md의 입력/출력 정의와 정합성이 올라간다.
- private simulator가 multi-step 호출을 평가할 경우 큰 점수 상승 가능성이 있다.

## Phase 3. `model_metadata` 기반 비용/모델 일반화

목표: public data의 고정 cost가 아니라 simulator가 제공하는 model metadata를 반영한다.

현재 문제:

- `submission.py`가 `model_metadata`를 버린다.
- `GeometricRouter`는 학습 데이터 평균 cost에 의존한다.
- private set에서 모델 이름, 비용, tier 구성이 바뀌면 취약하다.

개선 방향:

- `model_metadata` parser 추가
  - `model_id`
  - `cost`
  - `latency`
  - `quality_prior`가 있으면 사용
- route 호출 시 metadata가 있으면 `self.model_costs` 대신 request-local cost map 사용
- budget limit와 cost normalization을 request-local cost 기준으로 계산
- metadata에 unknown model이 들어오면 `cheap/mid/premium` rank mapping을 안전하게 처리

추가해야 할 테스트:

- cheap/mid/premium cost scale이 바뀌어도 가장 싼 충분 모델 선택
- premium cost가 낮아진 경우 premium 선택 허용
- unknown metadata field가 있어도 crash 없음
- model_metadata가 None이면 기존 artifact cost 사용

완료 기준:

- `submission.py`에서 `model_metadata`를 더 이상 버리지 않는다.
- 비용 scale 변화 테스트 통과
- 결과보고서에서 "모델 메타데이터 기반 동적 비용 반영"을 주요 기능으로 설명 가능

예상 점수 효과:

- private simulator 적응력 상승
- 하드코딩 라우터라는 인상 감소

## Phase 4. Evaluator와 training label 강화

목표: 수동 quality score 의존도를 줄이고, 대회 목표와 직접 맞는 `success`/`expected_min_model` 학습을 강화한다.

현재 문제:

- evaluator는 좋지만 데이터 규모가 작다.
- fallback quality score가 여전히 남아 있다.
- private 일반화를 위해 task 유형별 success label이 더 필요하다.

개선 방향:

- `data/public/example_eval_specs.csv`를 중심 데이터로 승격한다.
- `example_train.csv`의 `quality_score`는 evaluator 결과에서 자동 생성하는 흐름으로 전환한다.
- 각 task category별 최소 20개 이상의 synthetic/public style example을 만든다.
  - trivial exact answer
  - numeric check
  - short factual
  - code unit test
  - JSON/schema output
  - summarization constraint
  - architecture/rubric
  - missing context clarification
  - refusal/safety
- `expected_min_model` 분포 균형을 맞춘다.
  - cheap 40%
  - mid 35%
  - premium 20%
  - abstain 5%
- hard prompt에 대해 premium이 꼭 필요한 이유를 evaluator spec으로 표현한다.

추가해야 할 테스트:

- evaluator가 모든 evaluation_type에서 deterministic하게 동작
- labels 생성 시 expected_min_model이 의도대로 생성
- quality fallback 사용 비율을 리포트로 출력
- evaluator spec이 없는 데이터가 너무 많으면 경고

완료 기준:

- `fallback_quality_score` 의존 샘플 비율 30% 이하
- synthetic 포함 학습 prompt 200개 이상
- expected_min_model 분포 리포트 생성

예상 점수 효과:

- private generalization 상승
- 결과보고서의 "개발 과정 및 방법" 설명 강화

## Phase 4-A. 공개 AI 모델 및 데이터셋 활용 고도화

목표: 처음부터 모든 데이터를 직접 만들기보다, 검증된 공개 AI 모델과 공개 데이터셋을 활용해 라우터의 일반화 능력과 결과보고서 설득력을 높인다.

핵심 원칙:

- 생성형 LLM을 새로 파인튜닝하지 않는다.
- 공개 데이터셋은 라우팅 학습/평가 포맷으로 변환해 사용한다.
- 경량 임베딩 모델은 feature extractor로만 사용한다.
- 최종 라우팅 알고리즘과 budget-aware policy는 자체 구현으로 유지한다.

권장 조합:

```text
공개 라우팅/선호 데이터
        ↓
라우팅 학습 포맷 변환
        ↓
경량 임베딩 feature + 기존 geometric feature 결합
        ↓
expected_min_model / success / abstain label 학습
        ↓
Fast/Balanced/Premium budget-aware router 튜닝
```

### 활용 후보 1: RouteLLM

활용 목적:

- LLM 라우팅 문제의 선행 오픈소스 baseline으로 비교한다.
- cost-quality trade-off, threshold calibration, strong/weak model routing 개념을 참고한다.
- RouteLLM 방식과 본 프로젝트의 3-tier router 차이를 결과보고서에 설명한다.

적용 방식:

- RouteLLM 코드를 그대로 제출 라우터에 의존시키기보다, 벤치마크/비교 기준으로 사용한다.
- "RouteLLM은 2-model strong/weak routing에 강점이 있고, 본 프로젝트는 cheap/mid/premium/abstain과 budget tier를 지원하도록 확장했다"는 차별점을 만든다.
- RouteLLM 데이터셋 또는 threshold 아이디어를 참고하되, 최종 라우터는 `router_impls/geometric`의 자체 구현으로 유지한다.

붙임2/보고서 표현:

```text
RouteLLM 공개 연구와 데이터 구조를 참고하여 LLM routing 문제의 baseline과 평가 관점을 분석하고,
본 프로젝트에서는 3단계 모델 후보와 abstain action을 지원하는 자체 budget-aware router를 구현함.
```

### 활용 후보 2: LMSYS Chatbot Arena / MT-Bench Human Judgments

활용 목적:

- 실제 사용자 프롬프트와 사람 선호 판단을 이용해 "강한 모델이 필요한 프롬프트"를 추정한다.
- pairwise preference를 `strong_needed`, `weak_sufficient`, `uncertain` label로 변환한다.
- 라우터가 단순 길이/키워드가 아니라 실제 선호 데이터 기반으로 판단한다는 근거를 만든다.

적용 방식:

- prompt, model A/B output, human preference를 읽어 strong model win 여부를 만든다.
- 모델 강도 순위를 cheap/mid/premium proxy로 매핑한다.
- 선호 차이가 큰 샘플은 premium-needed 후보로, 약한 모델도 충분히 이긴 샘플은 cheap/mid 후보로 변환한다.
- 한국어가 적을 수 있으므로 직접 한국어 예제 데이터와 혼합한다.

주의점:

- 데이터에 유해/민감 대화가 포함될 수 있으므로 필터링한다.
- 개인 식별정보 가능성이 있는 샘플은 사용하지 않는다.
- 모델 출력 약관 책임이 있을 수 있으므로 원문 재배포 범위를 최소화하고, 변환된 feature/label 중심으로 사용한다.

붙임2/보고서 표현:

```text
LMSYS 공개 선호 데이터 중 개인정보·민감정보 가능성이 있는 샘플을 제외하고,
프롬프트와 선호 판단을 라우팅 학습용 strong-needed/weak-sufficient label로 변환하여 사용함.
원본 대화 전체를 모델 학습용 생성 데이터로 재배포하지 않고, 라우터 평가용 통계/라벨 중심으로 활용함.
```

### 활용 후보 3: PRM800K

활용 목적:

- 수학/추론 문제에서 쉬운 계산과 어려운 reasoning task를 구분한다.
- step-level correctness label을 이용해 단순 exact answer와 고난도 reasoning을 분리한다.
- 현재 라우터의 `numeric_check`, `exact_match`, `rubric_check` 평가기를 강화한다.

적용 방식:

- 문제 길이, 풀이 단계 수, 정답 형식, 오류 단계 수를 feature로 변환한다.
- 쉬운 산술/정답형 문제는 cheap label 후보로 사용한다.
- 다단계 reasoning이나 오류가 잦은 문제는 mid/premium 후보로 사용한다.
- 전체 원문을 과도하게 넣기보다 대표 샘플과 통계 기반 synthetic prompt 생성에 활용한다.

붙임2/보고서 표현:

```text
PRM800K의 수학/추론 correctness 정보를 활용해 reasoning 난이도별 라우팅 라벨을 보강함.
이를 통해 단순 계산형 프롬프트와 다단계 추론형 프롬프트를 구분하는 평가 데이터를 확장함.
```

### 활용 후보 4: 한국어 Instruction 데이터

후보:

- `CarrotAI/ko-instruction-dataset`
- `nlpai-lab/kullm-v2`
- 필요 시 AI Hub 한국어 데이터셋

활용 목적:

- 한국어 프롬프트 다양성을 보강한다.
- 결과보고서와 시연에서 한국어 사용성의 설득력을 높인다.
- short instruction, code request, summary request, QA, transformation task를 늘린다.

적용 방식:

- instruction만 사용하고 output은 라우팅 평가에 필요한 경우에만 사용한다.
- 프롬프트를 task_type, difficulty, expected_min_model 후보로 자동/수동 라벨링한다.
- 개인정보·민감정보·저작권 우려가 있는 샘플은 제외한다.
- 너무 긴 output 원문은 저장하지 않고 prompt와 라우팅 label 중심으로 변환한다.

붙임2/보고서 표현:

```text
한국어 instruction 공개 데이터셋에서 개인정보 및 민감정보 가능성이 있는 샘플을 제외하고,
프롬프트를 라우팅 평가 포맷(prompt, task_type, difficulty, expected_min_model)으로 변환하여 사용함.
```

### 활용 후보 5: 경량 임베딩 모델

권장 모델:

- `intfloat/multilingual-e5-small`
  - 한국어/영어 혼합 프롬프트에 적합하다.
  - 경량 다국어 임베딩 모델로 feature extractor에 쓰기 좋다.
- `sentence-transformers/all-MiniLM-L6-v2`
  - 영어 중심 prompt similarity에 적합하다.
- `BAAI/bge-small-en-v1.5`
  - 영어 중심 검색/유사도 feature에 적합하다.

권장 선택:

- 한국어 시연과 보고서까지 고려하면 `intfloat/multilingual-e5-small`을 1순위로 둔다.
- 모델을 로컬에 다운로드해 embedding feature만 생성하고, 라우터 runtime에서 외부 API를 호출하지 않는다.
- 대회 환경에서 모델 파일 다운로드가 어렵다면 embedding feature를 optional로 두고 기존 geometric feature만으로도 fallback되게 만든다.

구현 방향:

- `routing_stack/input/semantic_features.py` 추가
- 기본값은 외부 모델이 필요 없는 `hash-char-token-v1` encoder로 재현성을 유지
- optional dependency로 `sentence-transformers` 지원
- `scripts/build_semantic_feature_index.py`로 semantic centroid index 생성
- prompt embedding 원문을 직접 저장하지 않고 cheap/mid/premium centroid와 nearest distance/uncertainty feature만 artifact에 저장
- `GeometricRouter.fit(..., use_semantic_features=True)`와 학습 CLI `--semantic_features`로 기존 vector에 semantic feature를 추가

feature 예시:

```text
nearest_cheap_distance
nearest_mid_distance
nearest_premium_distance
semantic_uncertainty
```

현재 구현된 기반:

```text
routing_stack/input/semantic_features.py
routing_stack/input/tests/test_semantic_features.py
scripts/build_semantic_feature_index.py
router_impls/geometric/router.py 의 optional semantic_index 통합
router_impls/geometric/scripts/train_geometric_router.py --semantic_features
router_impls/geometric/tests/test_geometric_router.py 의 semantic 통합 테스트
```

semantic feature index 생성 예:

```powershell
python scripts\build_semantic_feature_index.py --input data\public\example_eval_specs.csv --output artifacts\semantic_feature_index.json
```

공개 임베딩 모델 사용 예:

```powershell
python scripts\build_semantic_feature_index.py --input data\public\example_eval_specs.csv --output artifacts\semantic_feature_index.json --encoder sentence-transformers --model intfloat/multilingual-e5-small
```

geometric router 학습 반영 예:

```powershell
python router_impls\geometric\scripts\train_geometric_router.py --semantic_features
```

붙임2 작성 방향:

```text
유형 1: 외부 모델 그대로 활용
기반 모델명 및 개발사: intfloat/multilingual-e5-small (intfloat)
기반 모델 라이선스: MIT
활용 목적: 프롬프트 임베딩 및 유사도 기반 라우팅 feature 추출
추가 학습 여부: 없음
가중치 배포 여부: 별도 재배포하지 않으며, 사용자는 공개 Hugging Face 저장소에서 직접 다운로드 가능
```

### 데이터 변환 파이프라인

추가할 스크립트:

```text
scripts/import_lmsys_preferences.py
scripts/import_prm800k_reasoning.py
scripts/import_korean_instruction.py
scripts/build_external_routing_dataset.py
scripts/filter_public_dataset.py
```

출력 파일:

```text
data/external/README.md
data/external/routing_prompts.csv
data/external/routing_labels.csv
data/external/external_eval_specs.csv
data/external/dataset_sources.json
data/external/filter_report.json
data/external/external_dataset_summary.json
```

현재 구현된 기반:

```text
data/external/README.md
data/external/dataset_sources.json
routing_stack/training/external_dataset.py
scripts/filter_public_dataset.py
scripts/import_korean_instruction.py
scripts/build_external_routing_dataset.py
routing_stack/training/tests/test_external_dataset.py
routing_stack/training/tests/test_import_korean_instruction.py
routing_stack/training/tests/test_build_external_routing_dataset.py
```

필터링 실행 예:

```powershell
python scripts\filter_public_dataset.py --input data\external\raw_candidates.csv --output data\external\routing_prompts.csv --report data\external\filter_report.json
```

한국어 instruction import 실행 예:

```powershell
python scripts\import_korean_instruction.py --input data\external\raw_ko_instruction.csv --output data\external\routing_prompts.csv --report data\external\filter_report.json
```

외부 prompt를 평가 명세로 변환하는 실행 예:

```powershell
python scripts\build_external_routing_dataset.py --input data\external\routing_prompts.csv --output data\external\external_eval_specs.csv --summary data\external\external_dataset_summary.json
```

공통 schema:

```csv
source,prompt_id,prompt,language,task_type,difficulty,risk_level,evaluation_type,expected_min_model,label_confidence,license,source_url
```

필터링 규칙:

- 이메일, 전화번호, 주민등록번호, 계좌번호, 주소 패턴 제거
- 욕설/혐오/자해/불법행위 prompt는 별도 safety/refusal bucket으로 분리
- 저작권이 있는 장문 원문 재배포 금지
- 출처 URL과 license를 row 또는 source manifest에 기록
- 원본 dataset 전체를 저장소에 넣지 않고 변환 샘플 또는 manifest 중심으로 관리

테스트:

- 외부 데이터 row에 source/license/source_url이 항상 존재하는지 검증
- PII pattern이 포함된 row가 filter되는지 검증
- 외부 prompt가 `example_eval_specs.csv` 호환 schema로 변환되는지 검증
- `test_spec`에 source/license/source_url/label_confidence가 보존되는지 검증
- expected_min_model 분포가 극단적으로 치우치지 않는지 검증
- external data 없이도 기존 tests가 통과하는지 검증

완료 기준:

- 외부 공개 데이터 기반 prompt 300개 이상 확보
- 한국어 prompt 100개 이상 확보
- source/license manifest 생성
- embedding feature optional path 구현
- Fast/Balanced simulation에서 비용 초과 감소와 품질 유지 확인

예상 점수 효과:

- 심사관에게 "공개 AI/데이터 생태계를 잘 활용했다"는 인상을 준다.
- 자체 synthetic 데이터만 쓴 경우보다 private 일반화 가능성이 높아진다.
- 붙임2의 AI 모델 활용 정보가 빈약하지 않고 명확해진다.
- 단, 라이선스/출처 관리가 부실하면 오히려 감점이므로 source manifest와 필터링 리포트를 반드시 같이 만든다.

## Phase 5. Policy tuning objective 재정의

목표: 실제 대회 평가식에 가까운 objective로 threshold를 튜닝한다.

현재 문제:

- 일반 simulation은 premium 과다 선택
- batch allocation은 under-route 증가
- threshold와 radius multiplier가 실제 점수와 직접 연결되지 않는다.

개선 방향:

- tier별 weighted score를 명시한다.

```text
score_tier = mean_quality - alpha_tier * mean_cost - beta_tier * budget_overflow - gamma_tier * under_route - delta_tier * over_route - epsilon_tier * should_abstain
final_score = 0.5 * fast + 0.3 * balanced + 0.2 * premium
```

- Fast의 `alpha`, `beta`를 가장 크게 둔다.
- under_route penalty는 premium-needed task에서 크게 적용한다.
- over_route penalty는 Fast에서 크게, Premium에서 작게 둔다.
- `router_impls/geometric/tuning.py`가 이 objective를 직접 최적화하게 한다.

추가해야 할 테스트:

- tuning 후 Fast premium selection 감소
- tuning 후 weighted score 개선
- tuning 결과가 artifact metadata에 저장

완료 기준:

- `artifacts/geometric_policy_report.json` 생성
- `policy_objective.overall_score`와 tier별 `weighted_score` 기록
- objective components와 penalties를 JSON에 저장
- 이전 정책과 개선 정책의 tier별 비교표 생성
- 결과보고서에 들어갈 핵심 수치 확정

예상 점수 효과:

- 심사관에게 "목표를 정확히 최적화했다"는 인상을 준다.

현재 구현된 기반:

```text
router_impls/geometric/tuning.py 의 TIER_OBJECTIVE_WEIGHTS
router_impls/geometric/tuning.py 의 score_tier_summary()
router_impls/geometric/tuning.py 의 score_policy_results()
router_impls/geometric/scripts/train_geometric_router.py --policy_report
router_impls/geometric/tests/test_geometric_router.py 의 objective regression tests
```

실행 예:

```powershell
python router_impls\geometric\scripts\train_geometric_router.py --policy_report artifacts\geometric_policy_report.json
```

리포트에 기록되는 핵심 지표:

```text
metadata.policy_objective.overall_score
metadata.policy_tuning.fast.weighted_score
metadata.policy_tuning.balanced.weighted_score
metadata.policy_tuning.premium.weighted_score
metadata.policy_tuning.{tier}.objective.components
metadata.policy_tuning.{tier}.objective.penalties
```

## Phase 6. 시연과 보고서용 evidence package 생성

목표: 심사관이 5분 안에 프로젝트의 가치를 이해하도록 산출물을 정리한다.

작업:

- `scripts/generate_report_assets.py` 추가
  - tier별 summary table 생성
  - selection distribution 생성
  - under_route/over_route 표 생성
  - before/after cost-quality 비교 생성
- `docs/report_assets/`에 CSV/JSON/이미지 저장
- viewer에서 보여줄 대표 prompt 6개 선정
  - trivial cheap
  - simple numeric
  - medium code
  - hard architecture
  - missing context abstain
  - tier별 선택 차이가 나는 prompt
- 시연 영상 흐름 정리
  - 프로젝트 문제 설명 20초
  - viewer 실행 30초
  - Fast/Balanced/Premium 비교 90초
  - evaluator/simulation 결과 60초
  - 오픈소스 구조와 라이선스 30초

완료 기준:

- 결과보고서에 넣을 표와 수치가 고정된다.
- 시연 영상 촬영 시나리오가 확정된다.

예상 점수 효과:

- 기술 구현이 보고서/시연에서 제대로 전달된다.

현재 구현된 기반:

```text
scripts/generate_report_assets.py
routing_stack/training/tests/test_generate_report_assets.py
docs/report_assets/tier_summary.csv
docs/report_assets/selection_distribution.csv
docs/report_assets/error_summary.csv
docs/report_assets/before_after.csv
docs/report_assets/demo_prompts.csv
docs/report_assets/fast_allocation_summary.csv
docs/report_assets/report_assets_summary.json
docs/report_assets/latency_summary.csv
docs/report_assets/latency_detail.csv
docs/report_assets/latency_report.json
docs/report_assets/submission_readiness.json
docs/report_assets/submission_check_run.json
```

실행 예:

```powershell
python scripts\generate_report_assets.py --output_dir docs\report_assets
python scripts\measure_router_latency.py --output_dir docs\report_assets --repeat 3
python scripts\verify_submission_readiness.py --output docs\report_assets\submission_readiness.json
python scripts\run_submission_checks.py --output docs\report_assets\submission_check_run.json
```

현재 고정된 보고서 수치:

```text
overall_weighted_score: 0.529
Fast: mean_quality 0.889, mean_cost 0.048, under_route 11/73, weighted_score 0.133
Balanced: mean_quality 0.926, mean_cost 0.097, under_route 0/73, weighted_score 0.217
Premium: mean_quality 0.926, mean_cost 0.099, under_route 0/73, weighted_score 0.179
Fast batch allocation: total_budget 2.19, total_cost 2.18, mean_cost 0.030
Local routing latency: Fast 5.97ms, Balanced 5.93ms, Premium 5.99ms
Submission readiness: 실제 GitHub URL, YouTube URL 입력 전까지 blocker 3개 유지
Submission check runner: strict readiness 없이 기본 재현 명령 passed
```

## Phase 7. 문서 최종화

목표: 제출 양식에 맞는 결과보고서와 붙임 자료를 완성한다.

결과보고서 5페이지 권장 구성:

1. 프로젝트 개요
   - 프로젝트명
   - GitHub URL
   - 시연영상 URL
   - 1~2줄 소개
2. 개발배경 및 목적
   - LLM 비용 낭비 문제
   - 저예산 tier 최적화 목표
3. 개발환경 및 아키텍처
   - Python, pandas/numpy/sklearn/lightgbm
   - `viewer -> router -> ai`
   - local-only routing
4. 주요 기능 및 기술
   - Geometric Router
   - OutputEvaluator
   - budget tier policy
   - history/output-aware routing
   - viewer
5. 구동 및 시연
   - 설치
   - 테스트
   - router server/viewer 실행
   - simulation 명령
6. 기대효과 및 활용분야
   - AI 비용 절감
   - 사내 AI gateway
   - 교육용 LLM 라우팅 실험 플랫폼
7. 혁신성 및 차별성
   - evaluator 기반 success label
   - cost-quality aware local routing
   - 외부 API 없는 simulator 친화 구조
8. 한계점 및 향후 로드맵
   - 작은 데이터
   - private distribution risk
   - output-aware evaluator 고도화
9. 소감 및 후기
   - 비용과 품질 균형을 정량화한 경험
   - 오픈소스 제출을 위한 재현성 정리 경험

붙임1 SBOM:

- requirements 기준 라이브러리 작성
- 라이선스 확인 후 표에 기재
- 공식 저장소 URL 포함

붙임2 AI 모델 활용 정보:

- 라우터는 LLM 가중치 모델이 아니라 routing policy임을 명확히 쓴다.
- Ollama/Qwen 등 로컬 모델을 시연에 사용했다면 유형 1에 해당하는지 검토한다.
- 제출물 핵심이 라우터 코드라면 "AI 모델은 선택적 시연 backend이며 라우터 판단은 로컬 코드"라고 설명한다.
- 코딩 보조용 상용 AI 사용 여부와 범위를 정직하게 기재한다.

완료 기준:

- HWPX 또는 DOCX 1부
- PDF 1부
- 회색 가이드 문구 삭제
- 맑은고딕 10pt 확인
- 5페이지 이내 확인
- 파일명 규칙 확인

현재 구현된 기반:

```text
docs/REPORT_OUTLINE.md
docs/SUBMISSION.md
docs/SBOM.md
docs/AI_MODEL_USAGE.md
docs/DEMO_SCRIPT.md
docs/report_assets/
LICENSE
```

현재 문서 상태:

- 결과보고서 본문 초안은 현재 라우터 기능, 성능 수치, report assets 기준으로 갱신됨
- `SUBMISSION.md`에 재현 명령, private adapter action schema, 제출 전 체크리스트 정리
- SBOM에 필수 의존성과 optional `sentence-transformers` 사용 조건 반영
- 붙임2에는 기본 경로와 optional 공개 임베딩 모델 사용 경로를 분리해 기재

남은 수동 작업:

- 실제 GitHub 공개 저장소 URL 입력
- 실제 YouTube 시연 영상 URL 입력
- 대회 양식 DOCX/HWPX에 `docs/REPORT_OUTLINE.md` 내용을 5페이지 이내로 배치
- PDF 변환 후 파일명 규칙 확인

## 7. 우선순위별 작업 목록

### P0. 반드시 해야 하는 작업

- `LICENSE` 추가
- `docs/SBOM.md` 작성
- `docs/AI_MODEL_USAGE.md` 작성
- 공개 데이터/AI 모델 활용 방침 확정
- 외부 데이터 source/license manifest 설계
- Fast/Balanced premium 과다 선택 완화
- `submission.py`에서 `history`, `model_metadata` 삭제 제거
- `select_output` action 설계 및 최소 구현
- 최종 simulation summary 생성
- 결과보고서 outline 작성

### P1. 점수를 크게 올리는 작업

- RouteLLM/LMSYS/PRM800K/한국어 instruction 데이터 import pipeline 추가
- `intfloat/multilingual-e5-small` 기반 optional embedding feature 추가
- online router와 batch allocator scoring 통합
- model_metadata 기반 request-local cost 반영
- evaluator spec 확장
- expected_min_model label 분포 균형화
- tuning objective를 tier-weighted score로 변경
- before/after 비교표 생성

### P2. 있으면 좋은 작업

- viewer에 history scenario 표시
- latency 측정 리포트 추가
- CLI 명령 통합
- report asset 자동 생성 스크립트
- README의 제출용 quickstart 정리

## 8. 권장 일정

제출 기한은 2026년 8월 27일 18:00이다. 현재 날짜 기준으로 남은 기간을 다음처럼 나눈다.

### 1주차: 제출 적합성 및 핵심 결함 제거

- LICENSE, SBOM, AI model usage 문서 추가
- `history`, `model_metadata` 인터페이스 반영
- Fast/Balanced budget guard 구현
- 제출 후보 테스트 안정화

### 2주차: 성능 개선

- 공개 데이터셋 import/filter pipeline 구현
- 경량 임베딩 feature optional 구현
- evaluator spec 확장
- expected_min_model 데이터 보강
- policy tuning objective 개선
- simulation before/after 비교 생성

### 3주차: 시연/문서화

- viewer demo scenario 확정
- 시연 영상 촬영
- 결과보고서 초안 작성
- 표와 수치 삽입

### 4주차: 제출 안정화

- 전체 테스트 실행
- clean clone 재현 확인
- DOCX/PDF 변환 확인
- 제출 파일명 확인
- 온라인 제출 전 최종 검토

## 9. 최종 성능 목표

현재 상태에서 현실적인 1차 목표는 다음이다.

| 항목 | 현재 관찰값 | 목표 |
| --- | ---: | ---: |
| Fast mean cost | 0.128 | 0.040 이하 |
| Fast cost over limit | 50/73 | 10/73 이하 |
| Fast mean quality | 0.967 또는 allocation 0.878 | 0.900 이상 |
| Fast under_route | allocation 20/73 | 10/73 이하 |
| Balanced mean cost | 0.135 | 0.090 이하 |
| Balanced cost over limit | 48/73 | 15/73 이하 |
| 제출 후보 테스트 | 77 passed | 통과 유지 |
| history 사용 | select_output 최소 구현 | history output 재사용 고도화 |
| model_metadata 사용 | request-local cost 반영 | private metadata schema 추가 적응 |

## 10. 결과보고서에서 쓰기 좋은 핵심 메시지

프로젝트 소개:

> 본 프로젝트는 사용자의 프롬프트 난이도와 예산 tier를 분석해 cheap, mid, premium, abstain 중 최적 action을 선택하는 로컬 LLM 라우터이다. 공개 라우팅/선호 데이터와 경량 임베딩 모델을 활용하되 외부 API 호출 없이 품질-비용 trade-off를 판단해 저예산 환경의 AI 운영 비용을 절감한다.

혁신성:

> 단순 키워드 분류가 아니라 후보 출력 평가 스펙과 공개 선호 데이터를 이용해 success/expected_min_model label을 만들고, pass probability와 sufficiency risk를 결합해 cheapest sufficient model을 찾는 구조를 구현했다.

한계점:

> 초기 버전은 내부 예제 데이터와 single-shot model selection 중심이었기 때문에 private distribution 일반화에는 한계가 있었다. 이를 보완하기 위해 RouteLLM/LMSYS/PRM800K/한국어 instruction 데이터 기반 라우팅 학습셋 확장, history 기반 output selection, metadata 기반 동적 비용 반영을 추진하고 있다.

향후 발전:

> 사내 AI gateway, 로컬 LLM orchestration, 교육용 LLM 비용 실험 플랫폼, 온디바이스 AI 라우팅 정책 엔진으로 확장할 수 있다.

## 11. 최종 권장 개발 방향

현재 프로젝트는 이미 "구조가 있는 라우터 MVP"이다. 다음 단계에서 가장 중요한 것은 기능을 무작정 늘리는 것이 아니라, 심사관이 보는 핵심 질문에 직접 답하는 것이다.

핵심 질문:

- Fast tier에서 정말 돈을 아끼는가?
- 돈을 아끼면서 어려운 문제를 놓치지 않는가?
- 이미 호출한 결과를 재사용해 중복 비용을 줄이는가?
- private simulator 입력을 제대로 사용하는가?
- 오픈소스 프로젝트로 재현 가능하고 라이선스가 명확한가?

따라서 고도화의 중심은 다음 세 가지로 압축한다.

1. Budget-aware routing을 실제 `route()` 선택 로직에 통합한다.
2. `history`와 `model_metadata`를 활용하는 simulator adapter를 완성한다.
3. 공개 라우팅/선호 데이터와 경량 임베딩 모델을 활용해 라우터 feature와 학습 데이터를 강화한다.
4. 결과보고서, SBOM, AI 모델 활용 명세, 시연 자료를 제출 가능한 수준으로 정리한다.

이 네 가지가 완료되면 현재 60점대 후반 수준의 프로젝트를 80점대 후보로 끌어올릴 수 있다.
