# 라우터 오케스트레이션 설계

이 문서는 `plan.md`를 실제 구현 가능한 설계로 구체화합니다. 목표는 프로젝트 범위 안에서 기존 `geometric`, `quality_utility` 라우터를 비교하고, 불확실한 요청만 별도 처리하는 로컬 오케스트레이션 계층을 추가하는 것입니다.

## 설계 원칙

1. 라우팅 판단은 로컬 코드로만 수행합니다.
2. 외부 LLM API, 외부 네트워크 서비스, 실시간 웹 호출은 사용하지 않습니다.
3. 라우터는 답변을 생성하지 않습니다.
4. 최종 선택은 `cheap`, `mid`, `premium`, `abstain` 중 하나입니다.
5. 기존 `viewer -> router -> ai` 실행 구조를 깨지 않습니다.
6. 새 기능은 먼저 `experiments`에서 검증하고, 성능이 확인된 뒤 서버 기본 경로에 연결합니다.

## 현재 구조

현재 실행 경로는 다음과 같습니다.

```text
viewer
  ↓
viewer_server
  ↓
router_server
  ↓
normalize_input()
  ↓
RouteRequest
  ↓
selected router adapter
  ↓
LocalAI
```

현재 `router_server`는 사용자가 선택한 단일 라우터만 호출합니다.

```text
payload.router = geometric | quality_utility
```

따라서 아직 여러 라우터 결과를 종합하는 계층은 없습니다.

## 목표 구조

오케스트레이션을 켜면 실행 경로는 다음처럼 확장됩니다.

```text
viewer
  ↓
router_server
  ↓
Input Normalizer
  ↓
Base Router Runner
  ├─ geometric
  └─ quality_utility
  ↓
Uncertainty Detector
  ↓
Orchestrator
  ↓
Final RouteResult
  ↓
LocalAI
```

기본 단일 라우터 모드는 그대로 유지합니다.

```text
router=geometric
router=quality_utility
router=orchestrator
```

`orchestrator`는 새 adapter처럼 등록할 수 있게 설계합니다.

## 모듈 구조

추가할 모듈은 다음과 같습니다.

```text
routing_stack/
  planning/
    __init__.py
    geometric_signals.py
    uncertainty.py
    orchestrator.py
    types.py

  experiments/
    router_compare.py
    orchestrator_eval.py
```

역할:

- `types.py`: planning 계층에서 쓰는 dataclass 정의
- `geometric_signals.py`: geometric 라우터 고유 신호를 orchestrator가 쓰기 쉬운 형태로 변환
- `uncertainty.py`: 라우터 결과와 geometric 신호 기반의 불확실성 판단
- `orchestrator.py`: 여러 라우터 결과를 하나의 `RouteResult`로 합성
- `orchestrator_eval.py`: public set 기반 비교 실험

## 데이터 계약

### NormalizedInput

이미 구현된 계약입니다.

```python
@dataclass(frozen=True)
class NormalizedInput:
    input_type: str
    text: str
    router_features: dict[str, Any]
    metadata: dict[str, Any]
```

현재는 `input_type="text"`만 지원합니다.

미래 입력 확장:

```text
file  -> text summary + file feature
image -> OCR/text summary + visual feature
pdf   -> extracted text + page/table feature
```

단, router는 원본 파일을 직접 보지 않습니다.

### RouteRequest

현재 계약을 유지합니다.

```python
@dataclass
class RouteRequest:
    prompt: str
    tier: str = "balanced"
    task_type: str = ""
    difficulty: str = ""
    risk_level: str = ""
    evaluation_type: str = ""
    input_features: dict[str, Any] = field(default_factory=dict)
```

orchestrator도 동일한 `RouteRequest`를 받습니다.

### RouterObservation

여러 라우터 결과를 표준화하기 위한 내부 표현입니다.

```python
@dataclass(frozen=True)
class RouterObservation:
    router_name: str
    selected_model_id: str
    selection_reason: str
    model_quality: dict[str, float | None]
    model_utility: dict[str, float | None]
    model_cost: dict[str, float | None]
    raw_result: RouteResult
```

`model_quality` 변환 규칙:

1. `policy_quality`
2. `calibrated_quality`
3. `predicted_quality`
4. `pass_probability`
5. `candidate.score`

위 순서로 후보 metric에서 값을 찾습니다.

### UncertaintySignal

불확실성 판단 결과입니다.

```python
@dataclass(frozen=True)
class UncertaintySignal:
    uncertain: bool
    confidence: float
    reason: str
    signals: dict[str, bool]
    metrics: dict[str, float]
```

예:

```json
{
  "uncertain": true,
  "confidence": 0.41,
  "reason": "router_disagreement",
  "signals": {
    "router_disagreement": true,
    "small_quality_margin": false,
    "high_cost_pressure": true,
    "missing_context": false
  },
  "metrics": {
    "quality_margin": 0.04,
    "cost_pressure": 0.71,
    "selected_quality": 0.62
  }
}
```

### GeometricSignals

`geometric` 라우터는 단순히 최종 선택 모델만 내는 것이 아니라, 각 모델의 성공 영역과 입력 사이의 관계를 설명합니다. orchestrator는 이 정보를 별도 구조로 표준화해서 사용합니다.

```python
@dataclass(frozen=True)
class GeometricSignals:
    available: bool
    selected_model_id: str | None
    selection_reason: str | None
    simple_prompt_prior: bool
    frontier_model_id: str | None
    model_distance: dict[str, float | None]
    normalized_distance: dict[str, float | None]
    pass_probability: dict[str, float | None]
    sufficiency_probability: dict[str, float | None]
    feasible: dict[str, bool]
    signals: dict[str, bool]
```

예:

```json
{
  "available": true,
  "selected_model_id": "cheap",
  "selection_reason": "simple_prompt_prior",
  "simple_prompt_prior": true,
  "frontier_model_id": "cheap",
  "model_distance": {
    "cheap": 31.5,
    "mid": 17.3,
    "premium": 5.7
  },
  "normalized_distance": {
    "cheap": 5.6,
    "mid": 7.0,
    "premium": 7.1
  },
  "pass_probability": {
    "cheap": 0.32,
    "mid": 0.54,
    "premium": 0.75
  },
  "sufficiency_probability": {
    "cheap": 0.30,
    "mid": 0.52,
    "premium": 0.83
  },
  "feasible": {
    "cheap": false,
    "mid": false,
    "premium": false
  },
  "signals": {
    "cheap_geometrically_safe": false,
    "only_premium_near": false,
    "all_envelopes_far": true,
    "high_under_route_risk": true
  }
}
```

`GeometricSignals`는 `RouteResult.diagnostics`와 `RouteResult.candidates[*].metrics`에서만 만들어야 합니다. geometric 구현체를 직접 들여다보거나 별도 private method에 의존하지 않습니다.

## Geometric Signal Extractor 설계

구현 위치:

```text
routing_stack/planning/geometric_signals.py
```

함수 시그니처:

```python
def extract_geometric_signals(result: RouteResult | None) -> GeometricSignals:
    ...
```

입력:

- `geometric` adapter가 반환한 `RouteResult`
- geometric 결과가 없으면 `available=False`를 반환합니다.

추출 대상:

```text
diagnostics.evidence.simple_prompt_prior
diagnostics.frontier_hint.model_id
candidates[*].metrics.distance
candidates[*].metrics.normalized_distance
candidates[*].metrics.pass_probability
candidates[*].metrics.sufficiency_probability
candidates[*].metrics.feasible
```

파생 신호:

#### cheap_geometrically_safe

cheap이 geometric 기준으로 충분히 안전하면 true입니다.

초기 기준:

```text
cheap.feasible == true
or cheap.pass_probability >= 0.74
or simple_prompt_prior == true
```

Fast tier에서 premium escalation을 막는 강한 근거로 사용합니다.

#### mid_geometrically_safe

mid가 geometric 기준으로 충분히 안전하면 true입니다.

초기 기준:

```text
mid.feasible == true
or mid.pass_probability >= 0.82
```

Balanced tier에서 premium 대신 mid를 선택할 근거로 사용합니다.

#### only_premium_near

premium만 envelope에 가깝고 cheap/mid는 멀면 true입니다.

초기 기준:

```text
premium.normalized_distance <= 1.25
cheap.normalized_distance >= 2.0
mid.normalized_distance >= 1.6
```

Premium tier에서 premium을 허용하는 근거로 사용합니다.

#### all_envelopes_far

모든 모델이 성공 envelope에서 멀면 true입니다.

초기 기준:

```text
min(normalized_distance.values()) >= 2.5
```

이 경우 모델 선택보다 missing context 또는 abstain 가능성을 확인해야 합니다.

#### high_under_route_risk

cheap 또는 mid 선택 시 부족할 가능성이 높으면 true입니다.

초기 기준:

```text
cheap.sufficiency_probability < 0.45
and mid.sufficiency_probability < 0.65
```

Premium tier에서는 escalation 근거가 될 수 있지만, Fast tier에서는 비용 제약과 함께 판단합니다.

## Uncertainty Detector 설계

함수 시그니처:

```python
def assess_uncertainty(
    observations: list[RouterObservation],
    input_features: dict[str, Any],
    tier: str,
    geometric_signals: GeometricSignals | None = None,
) -> UncertaintySignal:
    ...
```

### 판단 신호

#### 1. router_disagreement

두 개 이상의 라우터가 서로 다른 모델을 선택하면 true입니다.

```text
geometric -> cheap
quality_utility -> premium
=> router_disagreement = true
```

단, `abstain`과 모델 선택이 갈리는 경우는 강한 disagreement로 봅니다.

#### 2. small_quality_margin

각 라우터의 모델별 품질 예측에서 1등과 2등 차이가 작으면 true입니다.

초기 기준:

```text
quality_margin < 0.08
```

라우터마다 scale이 다르므로 margin은 가능하면 정규화해서 계산합니다.

정규화 방식:

```text
normalized_quality = (value - min(values)) / (max(values) - min(values))
```

모든 값이 같거나 결측이면 margin은 0으로 봅니다.

#### 3. low_selected_quality

선택된 모델의 품질 예측이 낮으면 true입니다.

초기 기준:

```text
selected_quality < 0.55
```

quality scale이 다른 라우터가 있으므로 1차 구현에서는 보조 신호로만 사용합니다.

#### 4. high_cost_pressure

입력 feature가 비용이 많이 들 가능성을 보이면 true입니다.

초기 기준:

```text
estimated_input_tokens >= 1200
estimated_output_tokens >= 1600
code_token_pressure >= 0.65
json_or_table_pressure >= 0.65
```

Fast tier에서는 더 민감하게 봅니다.

```text
Fast:
  estimated_input_tokens >= 700
  estimated_output_tokens >= 900
```

#### 5. missing_context

`input_features["missing_context"] == true`이면 true입니다.

이 경우 premium으로 올리는 것보다 `abstain` 또는 clarification 성격의 선택이 더 낫습니다.

#### 6. high_premium_gap

premium 예측 품질이 cheap보다 많이 높으면 true입니다.

초기 기준:

```text
premium_quality - cheap_quality >= 0.25
```

이 신호는 Premium tier에서 premium 선택을 허용하는 근거가 됩니다.

#### 7. geometric_out_of_distribution

geometric 기준으로 모든 모델 envelope에서 멀면 true입니다.

```text
geometric_signals.signals["all_envelopes_far"] == true
```

이 신호는 “무조건 premium” 근거가 아니라 “기존 라우터가 낯선 입력을 보고 있다”는 불확실성 근거입니다.

#### 8. geometric_cheap_safe

geometric 기준으로 cheap이 안전하면 true입니다.

```text
geometric_signals.signals["cheap_geometrically_safe"] == true
```

Fast tier에서는 불확실성을 낮추는 방향으로 사용합니다.

#### 9. geometric_only_premium_near

premium만 geometric envelope에 가깝다면 true입니다.

```text
geometric_signals.signals["only_premium_near"] == true
```

Premium tier에서는 escalation 근거가 되지만, Fast tier에서는 단독으로 premium 선택 근거가 되지 않습니다.

### confidence 계산

초기 confidence는 단순 점수 방식으로 계산합니다.

```text
confidence = 1.0
confidence -= 0.25 if router_disagreement
confidence -= 0.20 if small_quality_margin
confidence -= 0.15 if low_selected_quality
confidence -= 0.15 if high_cost_pressure
confidence -= 0.20 if missing_context
confidence -= 0.15 if geometric_out_of_distribution
confidence += 0.10 if geometric_cheap_safe and tier == "fast"
```

범위:

```text
0.0 <= confidence <= 1.0
```

불확실성 판정:

```text
uncertain = confidence < 0.70
```

Fast tier에서는 더 보수적으로 봅니다.

```text
Fast:
  uncertain = confidence < 0.78
```

## Orchestrator 설계

함수 시그니처:

```python
def orchestrate_route(
    request: RouteRequest,
    observations: list[RouterObservation],
    uncertainty: UncertaintySignal,
    geometric_signals: GeometricSignals | None = None,
) -> RouteResult:
    ...
```

### 기본 정책

#### 1. 확실하고 합의된 경우

두 라우터가 같은 모델을 선택하고 불확실하지 않으면 그 모델을 선택합니다.

```text
geometric -> cheap
quality_utility -> cheap
uncertain = false
=> cheap
```

#### 2. Fast tier

Fast tier의 우선순위는 비용 절감입니다.

정책:

- `missing_context`가 true이면 `abstain` 우선
- simple_directive가 true이면 `cheap` 우선
- geometric의 `cheap_geometrically_safe`가 true이면 `cheap` 우선
- premium은 강한 근거가 없으면 선택하지 않음
- high_cost_pressure가 true이면 output 비용까지 고려해서 cheap 또는 mid 우선

premium 허용 조건:

```text
high_premium_gap = true
and cheap_quality is very low
and at least one router selected premium
and not geometric_signals.signals["cheap_geometrically_safe"]
```

#### 3. Balanced tier

Balanced tier는 품질과 비용을 모두 봅니다.

정책:

- 두 라우터가 다르면 utility가 높은 쪽을 우선
- geometric의 `mid_geometrically_safe`가 true이고 premium과 mid 품질 차이가 작으면 mid
- premium과 mid 품질 차이가 작으면 mid
- cheap과 mid 품질 차이가 작으면 cheap
- missing_context는 abstain 우선

#### 4. Premium tier

Premium tier는 품질 손실을 줄입니다.

정책:

- high_premium_gap이 true면 premium 허용
- geometric의 `only_premium_near`가 true면 premium 선택 근거 강화
- premium 품질 우위가 작으면 mid 또는 cheap 유지
- simple_directive는 premium tier에서도 cheap 허용

### RouteResult 생성

orchestrator의 반환도 기존 계약을 따릅니다.

```python
RouteResult(
    router_name="orchestrator",
    selected_model_id=selected,
    action_type="call_model" 또는 "abstain",
    selection_reason=reason,
    candidates=merged_candidates,
    diagnostics={
        "observations": ...,
        "uncertainty": ...,
        "geometric_signals": ...,
        "policy": ...
    },
)
```

### 후보 병합

후보는 모델별로 하나씩 만듭니다.

```text
cheap
mid
premium
abstain
```

각 후보 metric:

```text
mean_quality
max_quality
mean_utility
min_cost
router_votes
selected_by
```

예:

```json
{
  "model_id": "cheap",
  "score": 0.82,
  "cost": 0.01,
  "metrics": {
    "mean_quality": 0.78,
    "mean_utility": 0.65,
    "router_votes": 2,
    "selected_by": ["geometric", "quality_utility"]
  }
}
```

## Orchestrator Adapter 설계

새 라우터처럼 등록합니다.

```text
routing_stack/adapters/orchestrator_adapter.py
```

역할:

1. 내부적으로 `geometric`, `quality_utility` adapter를 호출합니다.
2. `RouterObservation`으로 변환합니다.
3. geometric 결과에서 `extract_geometric_signals()`를 호출합니다.
4. `assess_uncertainty()`를 호출합니다.
5. `orchestrate_route()`로 최종 선택합니다.

등록:

```python
ROUTER_NAMES = ("geometric", "quality_utility", "orchestrator")
```

주의:

- 순환 import를 피하기 위해 registry에서 orchestrator adapter를 lazy import합니다.
- orchestrator는 실제 AI를 호출하지 않습니다.
- router server는 기존처럼 최종 `RouteResult.model_slot`만 보고 AI를 호출합니다.

## Experiment 설계

### router_compare 확장

현재 `router_compare.py`는 라우터별 결과를 JSON으로 출력합니다.

추가할 항목:

```text
uncertainty
geometric_signals
orchestrator_decision
```

옵션:

```powershell
python -m routing_stack.experiments.router_compare "..." --include_orchestrator
```

### orchestrator_eval

public set에서 라우터들을 비교합니다.

입력:

```text
data/public/example_train.csv
data/public/example_eval_specs.csv
```

비교 대상:

```text
geometric
quality_utility
orchestrator
```

출력:

```json
{
  "tier_summary": {
    "fast": {
      "mean_cost": 0.0,
      "mean_quality": 0.0,
      "selection_counts": {},
      "router_disagreement_count": 0,
      "uncertain_count": 0
    }
  }
}
```

초기 평가는 실제 private simulator가 아니라 public sample 기반의 근사 평가로 제한합니다.

## Viewer 설계

기본 화면은 유지합니다.

추가 정보는 접힌 패널에 넣습니다.

표시 항목:

- normalized input
- input features
- router observations
- uncertainty signal
- orchestrator final decision

표시 방식:

```text
기본:
  prompt
  AI output
  selected model

접힌 상세:
  router comparison
  uncertainty
  feature vector
```

## 테스트 설계

### uncertainty tests

파일:

```text
routing_stack/planning/tests/test_uncertainty.py
```

케이스:

1. 두 라우터가 같은 모델을 선택하면 uncertainty가 낮습니다.
2. 두 라우터가 다른 모델을 선택하면 `router_disagreement`가 true입니다.
3. 품질 margin이 작으면 `small_quality_margin`이 true입니다.
4. token pressure가 높으면 `high_cost_pressure`가 true입니다.
5. missing context면 `missing_context`가 true입니다.
6. geometric의 `all_envelopes_far`가 true이면 `geometric_out_of_distribution`이 true입니다.
7. Fast tier에서 `cheap_geometrically_safe`가 true이면 confidence가 일부 회복됩니다.

### geometric signal tests

파일:

```text
routing_stack/planning/tests/test_geometric_signals.py
```

케이스:

1. geometric result가 없으면 `available=False`입니다.
2. candidate metrics에서 distance, pass probability, feasible 값을 추출합니다.
3. `simple_prompt_prior`를 추출합니다.
4. cheap pass probability가 높으면 `cheap_geometrically_safe`가 true입니다.
5. premium만 normalized distance가 작으면 `only_premium_near`가 true입니다.
6. 모든 normalized distance가 크면 `all_envelopes_far`가 true입니다.

### orchestrator tests

파일:

```text
routing_stack/planning/tests/test_orchestrator.py
```

케이스:

1. 합의된 cheap 선택을 유지합니다.
2. Fast tier에서 단순 지시문은 cheap을 선택합니다.
3. Fast tier에서 `cheap_geometrically_safe`가 true이면 cheap을 선택합니다.
4. missing context는 abstain을 선택합니다.
5. Premium tier에서 premium 품질 격차가 크고 `only_premium_near`이면 premium을 선택합니다.
6. 반환값은 `RouteResult` 계약을 지킵니다.

### adapter tests

파일:

```text
routing_stack/adapters/tests/test_orchestrator_adapter.py
```

케이스:

1. orchestrator adapter가 두 base router를 호출합니다.
2. 최종 결과의 `router_name`은 `orchestrator`입니다.
3. diagnostics에 observations와 uncertainty가 들어갑니다.

## 구현 순서

### Phase 1. planning 타입과 uncertainty

파일:

```text
routing_stack/planning/types.py
routing_stack/planning/geometric_signals.py
routing_stack/planning/uncertainty.py
routing_stack/planning/tests/test_geometric_signals.py
routing_stack/planning/tests/test_uncertainty.py
```

완료 기준:

- geometric result에서 표준 geometric signal 추출
- fake observation 기반 테스트 통과
- 외부 API 호출 없음

### Phase 2. orchestrator 순수 함수

파일:

```text
routing_stack/planning/orchestrator.py
routing_stack/planning/tests/test_orchestrator.py
```

완료 기준:

- `orchestrate_route()`가 `RouteResult` 반환
- tier별 기본 정책 테스트 통과

### Phase 3. adapter 등록

파일:

```text
routing_stack/adapters/orchestrator_adapter.py
routing_stack/adapters/registry.py
```

완료 기준:

- `create_router("orchestrator")` 동작
- router server에서 `--routers orchestrator` 가능

### Phase 4. experiment 확장

파일:

```text
routing_stack/experiments/router_compare.py
routing_stack/experiments/orchestrator_eval.py
```

완료 기준:

- 단일 prompt에서 base router와 orchestrator 결과 비교
- public set 근사 평가 가능

### Phase 5. viewer 상세 패널

파일:

```text
routing_stack/viewer/app.js
routing_stack/viewer/index.html
routing_stack/viewer/styles.css
```

완료 기준:

- 기본 채팅 UI는 유지
- uncertainty와 orchestrator 상세는 접힌 패널에 표시

## 리스크와 대응

### 리스크 1. 라우터별 score scale이 다름

`geometric`의 `pass_probability`와 `quality_utility`의 `policy_quality`는 같은 의미가 아닙니다.

대응:

- 직접 평균하기 전에 min-max 정규화합니다.
- 초기 orchestrator는 score 평균보다 router vote와 tier 정책을 더 신뢰합니다.

### 리스크 2. Fast tier에서 premium 선택이 늘어날 수 있음

대응:

- Fast tier premium 선택 조건을 매우 엄격하게 둡니다.
- high_premium_gap만으로 premium을 선택하지 않습니다.
- cheap 품질이 낮고, 적어도 한 라우터가 premium을 선택한 경우에만 허용합니다.

### 리스크 3. public set overfit

대응:

- hard-coded prompt keyword를 늘리지 않습니다.
- feature와 uncertainty signal 중심으로 판단합니다.
- 회귀 케이스는 추가하되, 특정 문장만 맞추는 규칙은 피합니다.

### 리스크 4. 프로젝트 범위 초과

대응:

- 외부 AI Planner는 구현하지 않습니다.
- Local Planner도 기본 경로가 아니라 옵션으로 둡니다.
- 우선 `uncertainty + orchestrator`까지만 구현합니다.

## 성공 기준

1. 기존 라우터 단독 실행이 유지됩니다.
2. `orchestrator`를 새 router처럼 선택할 수 있습니다.
3. Fast tier에서 단순 요청은 cheap을 유지합니다.
4. 라우터가 애매한 요청을 `uncertainty`로 설명할 수 있습니다.
5. public set 실험에서 geometric/quality_utility/orchestrator를 비교할 수 있습니다.
6. 모든 로직은 로컬 코드로 동작합니다.
