# 라우터 오케스트레이션 확장 계획

이 문서는 현재 프로젝트 범위 안에서 `모델 라우터`를 `비용 인식 Task Planner + Model Router`로 확장하기 위한 단계별 계획입니다.

## 프로젝트 범위 기준

`PROJECT.md` 기준으로 반드시 지켜야 할 제약은 다음과 같습니다.

- 라우팅 로직은 로컬 코드로 동작해야 합니다.
- 외부 LLM API, 외부 네트워크 서비스, 실시간 API 호출은 라우터 판단에 사용할 수 없습니다.
- 최종 답변은 후보 모델 출력 중 하나를 선택해야 합니다.
- Fast / Balanced / Premium tier에서 비용 대비 품질을 높이는 것이 핵심입니다.
- 특히 Fast tier에서는 불필요한 상위 모델 호출을 줄여야 합니다.

따라서 이 프로젝트의 기본 제출 경로는 계속 다음 구조를 유지합니다.

```text
Input
  ↓
Input Normalizer
  ↓
Router Feature Vector
  ↓
Local Router
  ↓
cheap / mid / premium / abstain
```

AI Planner는 장기 확장 아이디어로 두되, 제출용 기본 경로에는 외부 AI 호출을 넣지 않습니다.

## 목표 구조

장기적으로는 다음 계층을 목표로 합니다.

```text
Text / File / Image / PDF input
        ↓
Input Normalizer
        ↓
Router Feature Vector
        ↓
Base Routers
  - geometric
  - quality_utility
        ↓
Uncertainty Detector
        ↓
Orchestrator
        ↓
Final Route Decision
```

옵션 확장:

```text
Uncertainty Detector
        ↓ 낮은 확신
Local AI Planner 또는 Offline Planner
        ↓
Orchestrator
```

단, 이 옵션은 로컬 모델 또는 사전 계산된 결과만 사용해야 합니다.

## Step 1. Input Normalizer 고정

상태: 일부 구현 완료

목표:

- router가 원본 파일, 이미지, PDF를 직접 보지 않게 합니다.
- 모든 입력은 `NormalizedInput`으로 변환합니다.
- 현재는 text만 지원하고, 파일/이미지/PDF는 계약만 열어둡니다.

구조:

```text
routing_stack/input/
  normalizer.py
  text_features.py
  token_estimator.py
```

완료 기준:

- `normalize_input({"input_type": "text", "prompt": ...})`가 동작합니다.
- router server가 `normalize_input()`을 통과합니다.
- `RouteRequest.input_features`에 router feature가 들어갑니다.
- image/pdf/file 입력은 아직 미지원이면 명확히 reject합니다.

## Step 2. Router Feature Vector 표준화

상태: 일부 구현 완료

목표:

- 라우터별 내부 feature는 달라도 공통 feature 이름은 유지합니다.
- Fast tier에서 중요한 비용/복잡도 feature를 공통화합니다.

공통 feature:

```text
prompt_length
whitespace_token_count
estimated_input_tokens
estimated_output_tokens
token_per_char
code_token_pressure
json_or_table_pressure
line_count
sentence_count
punctuation_ratio
digit_ratio
char_diversity
code_like
list_like
missing_context
simple_directive
```

완료 기준:

- `routing_stack/input/tests`에서 공통 feature를 검증합니다.
- `geometric`, `quality_utility` diagnostics에 같은 `input_features`가 포함됩니다.
- 신규 라우터도 이 feature를 재사용할 수 있습니다.

## Step 3. 모델별 품질 예측 비교 실험

상태: 일부 구현 완료

목표:

난이도 하나를 예측하지 않고 아래 값을 비교합니다.

```text
quality(prompt, cheap)
quality(prompt, mid)
quality(prompt, premium)
```

비교 도구:

```text
routing_stack/experiments/router_compare.py
```

출력:

```text
model_quality
model_utility
model_cost
selected_model_id
selection_reason
```

완료 기준:

- 같은 prompt/tier에 대해 `geometric`과 `quality_utility`를 비교할 수 있습니다.
- 결과는 JSON으로 저장 또는 출력할 수 있습니다.
- 회귀 케이스를 추가해 라우터 개선 전후를 비교할 수 있습니다.

## Step 4. Uncertainty Detector 추가

상태: 미구현

목표:

기존 라우터가 확신 있는 경우에는 그대로 결정하고, 애매한 경우만 별도 처리 대상으로 표시합니다.

입력:

```text
normalized_input
geometric result
quality_utility result
budget tier
```

판단 신호:

- 두 라우터의 선택 모델이 다릅니다.
- 후보 모델 간 품질 점수 차이가 작습니다.
- 선택 모델의 예상 품질이 낮습니다.
- premium 품질은 높지만 비용 페널티가 큽니다.
- input feature가 비용 압력을 크게 보입니다.
- missing_context가 true입니다.
- code_token_pressure 또는 json_or_table_pressure가 높습니다.

출력 예:

```json
{
  "uncertain": true,
  "reason": "router_disagreement",
  "confidence": 0.42,
  "signals": {
    "router_disagreement": true,
    "small_quality_margin": false,
    "high_cost_pressure": true
  }
}
```

구현 위치:

```text
routing_stack/planning/uncertainty.py
```

완료 기준:

- 외부 API 호출 없이 계산됩니다.
- 테스트용 fake router result로 불확실성 판단을 검증합니다.
- router server에는 바로 강제 적용하지 않고 experiment에서 먼저 검증합니다.

## Step 5. Orchestrator 추가

상태: 미구현

목표:

개별 라우터 결과를 종합해서 최종 route decision을 만듭니다.

구조:

```text
Base Routers
  ↓
Uncertainty Detector
  ↓
Orchestrator
  ↓
RouteResult
```

초기 정책:

- 두 라우터가 같은 모델을 선택하면 그대로 선택합니다.
- Fast tier에서 불확실하고 비용 압력이 낮으면 cheap 또는 mid를 우선합니다.
- Premium tier에서 불확실하고 품질 차이가 크면 premium을 허용합니다.
- missing context가 높으면 abstain 또는 clarification 성격의 후보를 우선합니다.

구현 위치:

```text
routing_stack/planning/orchestrator.py
```

완료 기준:

- `geometric`, `quality_utility` 결과를 입력으로 받아 하나의 `RouteResult`를 반환합니다.
- 기존 router adapter 계약을 깨지 않습니다.
- viewer/router/ai 3단계 실행 구조를 유지합니다.

## Step 6. Local Planner 옵션 검토

상태: 계획만 수립

목표:

무한한 prompt 종류에 대한 일반화를 높이기 위해 로컬 planner를 옵션으로 둡니다.

중요 제약:

- 외부 API를 호출하지 않습니다.
- 네트워크 서비스를 라우팅 판단에 사용하지 않습니다.
- 제출용 기본 경로에서는 비활성화합니다.

가능한 방식:

1. 로컬 소형 모델 사용
2. 사전 계산된 planner output 사용
3. public data에서 학습한 planner classifier 사용
4. rule + uncertainty 기반 pseudo planner 사용

출력 목표:

```json
{
  "task_type": "code_review",
  "reasoning_depth": 3,
  "needs_tool": false,
  "needs_file_context": false,
  "cheap_success": 0.45,
  "mid_success": 0.72,
  "premium_success": 0.9,
  "risk": "medium"
}
```

완료 기준:

- 로컬 실행만 지원합니다.
- planner 결과는 최종 답을 생성하지 않습니다.
- planner는 route decision의 보조 feature로만 사용합니다.

## Step 7. Viewer 반영

상태: 미구현

목표:

사용자는 기본적으로 단순한 채팅 UI를 보고, 필요할 때만 라우팅 상세를 펼쳐 봅니다.

추가 표시 항목:

- normalized input summary
- router feature vector summary
- uncertainty status
- router disagreement
- final orchestrator decision

주의:

- 기본 화면을 복잡하게 만들지 않습니다.
- 라우터 상세는 접힌 패널에 둡니다.

## Step 8. 평가 실험

상태: 미구현

목표:

새 구조가 실제로 Fast / Balanced tier에서 더 나은지 확인합니다.

비교 대상:

1. geometric 단독
2. quality_utility 단독
3. uncertainty + orchestrator
4. local planner 옵션

측정:

- tier별 평균 품질
- tier별 평균 비용
- Fast tier over-budget count
- under-route count
- router disagreement 케이스의 개선 여부

구현 위치:

```text
routing_stack/experiments/
  router_compare.py
  orchestrator_eval.py
```

## 우선순위

1. `Uncertainty Detector`
2. `Orchestrator`
3. public set 기반 비교 실험
4. viewer 상세 표시
5. local planner 옵션
6. file/image/pdf normalizer 확장

## 이번 프로젝트에서 하지 않을 것

- 외부 LLM API를 라우터 판단에 실시간 호출하지 않습니다.
- 웹 검색, OCR, PDF 파싱, 이미지 분석을 바로 구현하지 않습니다.
- 라우터가 최종 답변을 직접 생성하지 않습니다.
- 모델 선택을 넘어 실제 agent tool 실행까지 확장하지 않습니다.

## 다음 구현 작업

다음 단계는 `routing_stack/planning/uncertainty.py`를 추가하는 것입니다.

최소 구현 범위:

- `UncertaintySignal` dataclass
- `assess_uncertainty(results, input_features, tier)`
- router disagreement 감지
- quality margin 계산
- cost pressure 계산
- 테스트 추가

이 단계까지는 프로젝트 제약을 벗어나지 않고, 기존 라우터 구조에도 안전하게 붙일 수 있습니다.
