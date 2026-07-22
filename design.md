# Task Router 상세 설계

이 문서는 `plan.md`를 실제 구현 가능한 수준으로 구체화한 설계 문서입니다. 목적은 현재의 `prompt router`를 `task router`로 확장하되, `PROJECT.md`의 챌린지 범위를 벗어나지 않는 것입니다.

핵심은 다음과 같다.

```text
단일 프롬프트 난이도 예측
  ↓
전체 작업 컨텍스트 기반 모델별 성공 확률 예측
```

단, 라우터는 여전히 로컬 코드로만 동작해야 하며, 답변을 직접 생성하지 않는다.

## 1. 설계 목표

### 1.1 해결하려는 문제

현재 라우터는 `prompt` 하나를 기준으로 판단한다.

```text
prompt
  ↓
input_features
  ↓
router
```

이 방식은 다음 요청에서 구조적으로 불안정하다.

```text
다음 코드를 분석해줘
이거 수정해줘
나의 설계의 부족한 부분을 찾아줘
방금 말한 방식으로 구현해줘
```

이런 요청은 현재 문장만 보면 짧다. 하지만 실제 작업 난이도는 이전 대화, 첨부 파일, 코드 크기, 세션 상태, 이전 실패 이력에 의해 결정된다.

따라서 라우터 입력을 다음처럼 확장한다.

```text
prompt_features
+ context_features
+ call_history_features
  ↓
task_context_features
  ↓
router
```

### 1.2 성공 조건

1. 기존 prompt-only payload가 그대로 동작한다.
2. viewer가 최근 대화를 보내면 라우터가 context feature를 반영한다.
3. `다음 코드를 분석해줘`는 코드가 있으면 `missing_context=false`가 된다.
4. 참조 대상이 없으면 `missing_context=true`가 된다.
5. `orchestrator`가 context 기반 uncertainty를 diagnostics로 설명한다.
6. Fast tier에서 단순 요청은 계속 `cheap`을 선택한다.
7. 모든 판단은 로컬 deterministic 코드로 수행된다.

## 2. 최종 실행 흐름

```text
viewer
  ↓
router_server
  ↓
normalize_input(payload)
  ↓
resolve_context(payload, normalized_input)
  ↓
RouteRequest(
    prompt,
    tier,
    input_features,
    context_features,
    executor_context,
    call_history
  )
  ↓
selected router adapter
  ├─ geometric
  ├─ quality_utility
  └─ orchestrator
       ├─ geometric
       ├─ quality_utility
       ├─ geometric_signals
       ├─ uncertainty
       └─ final RouteResult
  ↓
LocalAI
```

`Context Resolver`는 두 종류의 출력을 만든다.

```text
router_context
  라우터가 보는 압축 feature

executor_context
  AI가 실제 답변 생성에 사용할 수 있는 상세 context
```

초기 구현에서는 `executor_context`를 응답 payload에 포함하고, AI 프롬프트 결합은 최소 범위로만 적용한다. 라우팅 정확도 개선이 우선이다.

## 3. 모듈 구조

추가할 구조:

```text
routing_stack/
  context/
    __init__.py
    types.py
    reference_detector.py
    state_summary.py
    context_features.py
    resolver.py
    tests/
      test_reference_detector.py
      test_context_features.py
      test_resolver.py
```

변경할 기존 파일:

```text
routing_stack/adapters/contract.py
routing_stack/app/router_server.py
routing_stack/input/text_features.py
routing_stack/planning/uncertainty.py
routing_stack/planning/orchestrator.py
routing_stack/viewer/app.js
routing_stack/experiments/router_compare.py
routing_stack/experiments/orchestrator_eval.py
README.md
```

## 4. 데이터 계약

### 4.1 ConversationMessage

파일:

```text
routing_stack/context/types.py
```

```python
@dataclass(frozen=True)
class ConversationMessage:
    role: str
    content: str
    created_at: str | None = None

    def to_dict(self) -> dict:
        ...
```

규칙:

- `role`은 `user`, `assistant`, `system`, `tool` 중 하나를 우선한다.
- 알 수 없는 role은 문자열로 보존한다.
- `content`는 앞뒤 공백을 제거한다.
- 빈 content 메시지는 resolver에서 버린다.

### 4.2 SessionState

```python
@dataclass(frozen=True)
class SessionState:
    summary: str = ""
    current_target: str = ""
    constraints: dict[str, Any] = field(default_factory=dict)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    previous_calls: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        ...
```

`artifacts` 예:

```json
[
  {
    "type": "code",
    "name": "router_server.py",
    "token_estimate": 1200,
    "language": "python"
  }
]
```

`previous_calls` 예:

```json
[
  {
    "model_id": "cheap",
    "success": false,
    "reason": "format_error",
    "cost": 0.01
  }
]
```

### 4.3 ReferenceSignal

```python
@dataclass(frozen=True)
class ReferenceSignal:
    has_reference_expression: bool
    reference_types: list[str]
    needs_resolution: bool
    matched_terms: list[str]

    def to_dict(self) -> dict:
        ...
```

`reference_types` 값:

```text
prior_context
artifact
code
file
design
previous_result
```

### 4.4 RoutingContext

```python
@dataclass(frozen=True)
class RoutingContext:
    current_prompt: str
    recent_messages: list[ConversationMessage]
    session_state: SessionState
    reference_signal: ReferenceSignal
    router_context: dict[str, Any]
    executor_context: dict[str, Any]
    context_confidence: float

    def to_dict(self) -> dict:
        ...
```

`router_context`는 라우터가 직접 사용할 feature다.

`executor_context`는 AI 실행 계층이 필요하면 사용할 상세 context다.

### 4.5 RouteRequest 확장

현재:

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

변경:

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
    context_features: dict[str, Any] = field(default_factory=dict)
    executor_context: dict[str, Any] = field(default_factory=dict)
    call_history: list[dict[str, Any]] = field(default_factory=list)
```

호환성:

- 기존 라우터는 `request.input_features`만 써도 동작한다.
- 새 라우터와 orchestrator는 `context_features`를 추가로 본다.
- `input_features`에는 현재 프롬프트 feature만 둔다.
- `context_features`에는 대화/상태/참조 feature만 둔다.
- `combined_features = {**input_features, **context_features}`는 서버 또는 adapter 내부에서 필요할 때만 만든다.

## 5. Reference Detector 설계

파일:

```text
routing_stack/context/reference_detector.py
```

### 5.1 함수

```python
def detect_references(prompt: str) -> ReferenceSignal:
    ...
```

### 5.2 규칙

참조 표현 그룹:

```python
PRIOR_CONTEXT_TERMS = (
    "이거", "그거", "저거", "아까", "방금", "위 내용", "위에서",
    "앞에서", "이전", "방금 말한", "아까 말한",
    "this", "that", "above", "previous", "earlier",
)

ARTIFACT_TERMS = (
    "첨부", "파일", "문서", "pdf", "엑셀", "이미지", "사진",
    "attached", "file", "document", "image",
)

CODE_TERMS = (
    "다음 코드", "아래 코드", "이 코드", "코드", "함수", "클래스",
    "에러", "버그", "스택트레이스",
    "code", "function", "class", "stack trace",
)

DESIGN_TERMS = (
    "나의 설계", "현재 설계", "이 설계", "구조", "아키텍처",
    "design", "architecture",
)

PREVIOUS_RESULT_TERMS = (
    "이전 결과", "방금 결과", "다시", "재시도", "고쳐서",
    "previous result", "retry",
)
```

### 5.3 출력 예

입력:

```text
나의 설계의 부족한 부분을 찾아줘
```

출력:

```json
{
  "has_reference_expression": true,
  "reference_types": ["design", "prior_context"],
  "needs_resolution": true,
  "matched_terms": ["나의 설계"]
}
```

입력:

```text
API가 무엇인지 한 문장으로 설명해줘
```

출력:

```json
{
  "has_reference_expression": false,
  "reference_types": [],
  "needs_resolution": false,
  "matched_terms": []
}
```

## 6. Context Resolver 설계

파일:

```text
routing_stack/context/resolver.py
```

### 6.1 함수

```python
def resolve_context(payload: dict[str, Any], normalized_input: NormalizedInput) -> RoutingContext:
    ...
```

### 6.2 입력 payload

기존 payload:

```json
{
  "prompt": "안녕?",
  "tier": "fast",
  "router": "orchestrator"
}
```

확장 payload:

```json
{
  "prompt": "다음 코드를 분석해줘",
  "tier": "balanced",
  "router": "orchestrator",
  "conversation": [
    {
      "role": "user",
      "content": "```python\nprint('hello')\n```"
    }
  ],
  "session_state": {
    "summary": "사용자는 LLM 라우터 프로젝트를 구현 중이다.",
    "current_target": "task router design",
    "artifacts": [
      {
        "type": "code",
        "name": "example.py",
        "token_estimate": 32
      }
    ]
  },
  "call_history": []
}
```

### 6.3 최근 대화 제한

초기 구현은 최근 10개 메시지만 사용한다.

```python
MAX_RECENT_MESSAGES = 10
MAX_MESSAGE_CHARS = 4000
```

규칙:

- 각 메시지는 최대 `MAX_MESSAGE_CHARS`까지만 feature 계산에 사용한다.
- 원문 전체를 라우터 feature에 넣지 않는다.
- `executor_context`에는 필요한 경우 잘린 preview만 포함한다.

### 6.4 참조 해결 알고리즘

```text
1. detect_references(current_prompt)
2. session_state.artifacts 확인
3. recent_messages에서 관련 payload 확인
4. session_state.current_target 확인
5. session_state.summary 확인
6. reference_resolved 판단
7. context_confidence 계산
```

참조 해결 기준:

```text
reference_types includes code
  resolved if recent_messages has code block
  or artifacts has type=code

reference_types includes artifact/file
  resolved if artifacts count > 0

reference_types includes design
  resolved if session_state.current_target exists
  or session_state.summary exists
  or recent_messages contains 설계/구조/design/architecture

reference_types includes prior_context
  resolved if recent_messages count > 0
  or session_state.summary exists
```

### 6.5 context_confidence

초기 점수 방식:

```text
confidence = 0.50
+ 0.20 if no reference expression
+ 0.25 if reference resolved
+ 0.10 if session_state.current_target exists
+ 0.10 if relevant artifact exists
+ 0.05 if recent_messages count > 0
- 0.20 if reference expression exists and not resolved
- 0.10 if prompt is very short and reference expression exists
```

범위:

```text
0.0 <= context_confidence <= 1.0
```

### 6.6 missing_context 결정

기존 `input_features["missing_context"]`는 현재 프롬프트만 본 초기 신호다.

Task Router에서는 최종 missing context를 다음으로 결정한다.

```text
prompt_missing_context = input_features["missing_context"]
reference_detected = reference_signal.has_reference_expression
reference_resolved = router_context["has_resolved_reference"]

if reference_detected and reference_resolved:
    final_missing_context = false
elif reference_detected and not reference_resolved:
    final_missing_context = true
else:
    final_missing_context = prompt_missing_context
```

그리고 다음 값을 `context_features`에 넣는다.

```text
prompt_missing_context
missing_context
has_reference_expression
has_resolved_reference
context_confidence
```

중요:

- `input_features["missing_context"]`는 보존한다.
- orchestrator와 uncertainty는 `context_features["missing_context"]`를 우선한다.
- context가 없으면 기존 동작과 최대한 비슷하게 fallback한다.

## 7. Context Feature 설계

파일:

```text
routing_stack/context/context_features.py
```

### 7.1 함수

```python
def build_context_features(
    prompt: str,
    recent_messages: list[ConversationMessage],
    session_state: SessionState,
    reference_signal: ReferenceSignal,
    input_features: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    ...
```

반환:

```text
(router_context, executor_context)
```

### 7.2 Router Context Fields

기본:

```text
has_reference_expression: bool
has_resolved_reference: bool
missing_context: bool
prompt_missing_context: bool
requires_cross_turn_reasoning: bool
context_confidence: float
conversation_message_count: int
user_message_count: int
assistant_message_count: int
```

토큰/비용:

```text
conversation_token_estimate: int
state_summary_token_estimate: int
artifact_token_estimate: int
context_token_estimate: int
estimated_total_input_tokens: int
estimated_total_output_tokens: int
context_token_pressure: float
history_token_pressure: float
artifact_token_pressure: float
```

참조/작업:

```text
reference_type_count: int
references_code: bool
references_file: bool
references_design: bool
references_previous_result: bool
has_current_target: bool
has_artifact: bool
has_code_artifact: bool
has_file_artifact: bool
```

이력:

```text
previous_call_count: int
previous_failure_count: int
retry_count: int
previous_cheap_failure: bool
previous_mid_failure: bool
```

출력 제약:

```text
output_format_constraint_count: int
tool_requirement_count: int
expected_output_complexity: float
```

### 7.3 Token Pressure

초기 기준:

```text
context_token_pressure = min(context_token_estimate / 6000, 1.0)
history_token_pressure = min(conversation_token_estimate / 4000, 1.0)
artifact_token_pressure = min(artifact_token_estimate / 6000, 1.0)
```

Fast tier 정책에서는 `context_token_pressure >= 0.65`를 비용 압박 신호로 쓴다.

### 7.4 Executor Context

초기 필드:

```json
{
  "summary": "...",
  "current_target": "...",
  "resolved_references": [
    {
      "source": "conversation",
      "type": "code",
      "preview": "```python\n..."
    }
  ],
  "artifact_summaries": [
    {
      "type": "code",
      "name": "router_server.py",
      "token_estimate": 1200
    }
  ]
}
```

초기에는 LocalAI에 원문 전체를 강제로 붙이지 않는다. 다만 이후 AI 호출 품질 개선을 위해 `LocalAI.run()`이 선택적으로 executor context를 받을 수 있게 확장할 수 있다.

## 8. State Summary 설계

파일:

```text
routing_stack/context/state_summary.py
```

### 8.1 함수

```python
def parse_session_state(payload: dict[str, Any]) -> SessionState:
    ...

def summarize_state_features(session_state: SessionState) -> dict[str, Any]:
    ...
```

### 8.2 세션 상태 파싱

허용 입력:

```json
{
  "summary": "...",
  "current_target": "...",
  "constraints": {},
  "artifacts": [],
  "previous_calls": []
}
```

`call_history`가 payload top-level에 있으면 `SessionState.previous_calls`와 병합한다.

중복 제거:

- 같은 `model_id`, `reason`, `created_at`이 있으면 하나로 본다.
- `created_at`이 없으면 순서를 유지한다.

## 9. Router Server 변경

파일:

```text
routing_stack/app/router_server.py
```

현재:

```python
normalized = normalize_input(payload)
input_features = normalized.router_features
request = RouteRequest(
    prompt=prompt,
    tier=...,
    input_features=input_features,
)
```

변경:

```python
normalized = normalize_input(payload)
routing_context = resolve_context(payload, normalized)
request = RouteRequest(
    prompt=normalized.text,
    tier=...,
    input_features=normalized.router_features,
    context_features=routing_context.router_context,
    executor_context=routing_context.executor_context,
    call_history=routing_context.session_state.previous_calls,
)
```

응답:

```python
return {
    "input": {
        **request.__dict__,
        "router": router_name,
        "normalized": normalized.to_dict(),
        "routing_context": routing_context.to_dict(),
    },
    "router": route_result.to_dict(),
    "ai": ai_result.to_dict(),
}
```

## 10. Router Adapter 적용

### 10.1 기존 adapter

`geometric`과 `quality_utility`는 당장 모델 구조를 크게 바꾸지 않는다.

초기 연결 방식:

```python
combined_features = {
    **request.input_features,
    **request.context_features,
}
```

그리고 diagnostics에 함께 기록한다.

```python
diagnostics["input_features"] = request.input_features
diagnostics["context_features"] = request.context_features
```

### 10.2 quality_utility

현재 LightGBM feature pipeline은 prompt text 기반일 가능성이 높다. 따라서 초기에는 ML 입력 feature를 바로 바꾸지 않고, policy prior 또는 utility 단계에서 context feature를 반영한다.

초기 보정 규칙:

```text
if context_features.missing_context:
    abstain 또는 낮은 품질로 처리

if previous_cheap_failure:
    cheap policy_quality 일부 감소

if references_code and context_token_pressure >= 0.40:
    cheap policy_quality 일부 감소
    mid policy_quality 일부 증가

if references_design and requires_cross_turn_reasoning:
    mid/premium policy_quality 일부 증가
```

이 보정은 hard-coded keyword 남발이 아니라 context resolver가 만든 구조화 feature를 사용한다.

### 10.3 geometric

geometric은 입력 feature vector를 직접 구성하므로 다음 feature를 추가 후보로 둔다.

```text
requires_cross_turn_reasoning
context_token_pressure
artifact_token_pressure
previous_failure_count_norm
reference_resolved
```

단, artifact를 다시 학습해야 하므로 1차 구현에서는 diagnostics와 orchestrator policy에서 먼저 사용한다. geometric vector 확장은 별도 학습 단계로 분리한다.

## 11. Uncertainty 확장

파일:

```text
routing_stack/planning/uncertainty.py
```

현재 주요 신호:

```text
router_disagreement
small_quality_margin
low_selected_quality
high_cost_pressure
missing_context
high_premium_gap
geometric_out_of_distribution
geometric_cheap_safe
geometric_only_premium_near
```

추가 신호:

```text
context_missing
reference_unresolved
cross_turn_required
context_cost_pressure
previous_failure
previous_cheap_failure
low_context_confidence
```

판단:

```text
context_missing = context_features["missing_context"]
reference_unresolved =
    has_reference_expression and not has_resolved_reference

cross_turn_required =
    requires_cross_turn_reasoning

context_cost_pressure =
    context_token_pressure >= 0.65

previous_failure =
    previous_failure_count > 0

low_context_confidence =
    context_confidence < 0.55
```

confidence 보정:

```text
confidence -= 0.25 if reference_unresolved
confidence -= 0.15 if low_context_confidence
confidence -= 0.15 if context_cost_pressure
confidence -= 0.10 if previous_failure
confidence += 0.10 if has_resolved_reference and context_confidence >= 0.80
```

중요:

- `reference_unresolved`는 premium 선택 근거가 아니다.
- 참조가 해결되지 않았으면 premium을 호출해도 성공 가능성이 낮으므로 abstain 쪽으로 간다.

## 12. Orchestrator 정책 확장

파일:

```text
routing_stack/planning/orchestrator.py
```

### 12.1 공통 우선순위

```text
1. context_features.missing_context == true
   => abstain

2. simple_directive == true and no cross-turn reference
   => cheap

3. previous_cheap_failure == true
   => cheap 선택 억제

4. resolved code/design reference
   => mid 이상 후보 강화

5. tier별 비용-품질 정책 적용
```

### 12.2 Fast tier

```text
if missing_context:
    abstain

if simple_directive and not requires_cross_turn_reasoning:
    cheap

if has_resolved_reference and context_token_pressure < 0.25:
    cheap 또는 mid 허용

if references_code and context_token_pressure >= 0.25:
    mid 우선

premium은 다음 조건을 모두 만족할 때만 허용:
    high_premium_gap
    cheap_quality < 0.45
    at least one router selected premium
    not geometric_cheap_safe
    not reference_unresolved
```

### 12.3 Balanced tier

```text
if missing_context:
    abstain

if previous_cheap_failure:
    cheap 제외 후 utility 비교

if references_code or references_design:
    mid 이상 후보 우선

if premium과 mid 품질 차이가 작으면 mid
if mid와 cheap 품질 차이가 작고 context pressure가 낮으면 cheap
```

### 12.4 Premium tier

```text
if missing_context:
    abstain

if simple_directive and not requires_cross_turn_reasoning:
    cheap

if previous_mid_failure or high_premium_gap:
    premium 허용

if premium 품질 우위가 작으면 mid 유지
```

## 13. missing_context 정책 재정의

### 13.1 기존 신호의 위치 변경

`routing_stack/input/text_features.py`의 `missing_context`는 삭제하지 않는다. 대신 의미를 바꾼다.

현재 의미:

```text
이 프롬프트는 context가 부족하다
```

변경 후 의미:

```text
이 프롬프트는 context 참조가 의심된다
```

권장 필드명 변경:

```text
missing_context -> prompt_missing_context
```

다만 하위 호환을 위해 기존 key는 유지하고, Context Resolver에서 다음 값을 새로 만든다.

```text
context_features["missing_context"]
context_features["prompt_missing_context"]
```

### 13.2 예시

#### 케이스 A

```json
{
  "prompt": "다음 코드를 분석해줘",
  "conversation": [
    {"role": "user", "content": "```python\nprint(1)\n```"}
  ]
}
```

결과:

```json
{
  "prompt_missing_context": true,
  "has_reference_expression": true,
  "has_resolved_reference": true,
  "missing_context": false
}
```

#### 케이스 B

```json
{
  "prompt": "다음 코드를 분석해줘",
  "conversation": []
}
```

결과:

```json
{
  "prompt_missing_context": true,
  "has_reference_expression": true,
  "has_resolved_reference": false,
  "missing_context": true
}
```

#### 케이스 C

```json
{
  "prompt": "이모티콘좀 그만 써라"
}
```

결과:

```json
{
  "prompt_missing_context": false,
  "has_reference_expression": false,
  "has_resolved_reference": false,
  "missing_context": false,
  "simple_directive": true
}
```

## 14. Viewer 설계

파일:

```text
routing_stack/viewer/app.js
```

### 14.1 conversation 상태

브라우저에서 최근 대화를 배열로 유지한다.

```javascript
let conversation = [];
const MAX_CONVERSATION_MESSAGES = 10;
```

전송 전:

```javascript
payload.conversation = conversation.slice(-MAX_CONVERSATION_MESSAGES);
```

응답 후:

```javascript
conversation.push({ role: "user", content: prompt });
conversation.push({ role: "assistant", content: ai.output || "" });
```

새 대화:

```javascript
conversation = [];
```

주의:

- 현재 요청을 conversation에 넣기 전에 payload를 만든다.
- 그래야 `conversation`은 “이전 대화”만 의미한다.

### 14.2 라우팅 상세 표시

`routerDecision`에 다음 항목을 추가한다.

```text
context_confidence
missing_context
has_reference_expression
has_resolved_reference
requires_cross_turn_reasoning
context_token_estimate
```

기본 채팅 화면은 유지하고, 상세 패널에서만 표시한다.

## 15. Experiment 설계

### 15.1 router_compare 확장

파일:

```text
routing_stack/experiments/router_compare.py
```

CLI 옵션:

```powershell
python -m routing_stack.experiments.router_compare "다음 코드를 분석해줘" --context_json examples/context/code_context.json --include_orchestrator
```

`context_json` 예:

```json
{
  "conversation": [
    {
      "role": "user",
      "content": "```python\nprint('hello')\n```"
    }
  ],
  "session_state": {
    "summary": "사용자는 Python 코드 분석을 요청 중이다.",
    "current_target": "example.py"
  },
  "call_history": []
}
```

출력에 추가:

```json
{
  "routing_context": {},
  "context_features": {},
  "planning": []
}
```

### 15.2 orchestrator_eval 확장

public set은 단일 prompt 중심이므로 context 평가는 별도 fixture를 만든다.

```text
examples/context/
  code_context.json
  design_context.json
  unresolved_reference.json
```

`orchestrator_eval`에는 optional context fixture를 주입할 수 있게 한다.

```powershell
python -m routing_stack.experiments.orchestrator_eval --context_fixture examples/context/design_context.json
```

## 16. 테스트 설계

### 16.1 reference detector tests

파일:

```text
routing_stack/context/tests/test_reference_detector.py
```

케이스:

1. `다음 코드를 분석해줘`는 `code`, `prior_context` 참조로 본다.
2. `나의 설계의 부족한 부분을 찾아줘`는 `design` 참조로 본다.
3. `API가 무엇인지 설명해줘`는 참조 표현 없음.
4. `첨부한 파일 요약해줘`는 `file` 또는 `artifact` 참조로 본다.

### 16.2 context feature tests

파일:

```text
routing_stack/context/tests/test_context_features.py
```

케이스:

1. conversation 메시지 수와 token estimate 계산.
2. artifacts의 type별 count 계산.
3. previous failure count 계산.
4. context token pressure 계산.

### 16.3 resolver tests

파일:

```text
routing_stack/context/tests/test_resolver.py
```

케이스:

1. prompt-only payload는 context feature 기본값을 만든다.
2. `다음 코드를 분석해줘` + 이전 대화 코드 있음은 resolved.
3. `다음 코드를 분석해줘` + 이전 대화 없음은 missing.
4. `나의 설계...` + session_state.current_target 있음은 resolved.
5. `context_confidence`는 0.0~1.0 사이.

### 16.4 router server tests

파일:

```text
routing_stack/app/tests/test_routing_stack.py
```

추가 케이스:

1. route response에 `routing_context`가 포함된다.
2. context payload가 없어도 기존 요청이 통과한다.
3. conversation에 코드가 있으면 `context_features["missing_context"] == False`.

### 16.5 orchestrator tests

파일:

```text
routing_stack/planning/tests/test_orchestrator.py
```

추가 케이스:

1. missing context면 abstain.
2. simple directive + cross-turn 없음이면 cheap.
3. previous cheap failure면 cheap 선택을 피한다.
4. resolved code reference는 Fast에서 mid를 허용한다.
5. unresolved reference는 Premium에서도 premium으로 보내지 않는다.

## 17. 구현 순서

### Phase 1. Context 기본 계층

구현:

```text
routing_stack/context/types.py
routing_stack/context/reference_detector.py
routing_stack/context/state_summary.py
routing_stack/context/context_features.py
routing_stack/context/resolver.py
```

검증:

```powershell
python -m pytest routing_stack\context\tests -q
```

### Phase 2. 서버 계약 연결

구현:

```text
routing_stack/adapters/contract.py
routing_stack/app/router_server.py
```

검증:

```powershell
python -m pytest routing_stack\app\tests routing_stack\context\tests -q
```

### Phase 3. missing_context 정책 변경

구현:

```text
routing_stack/planning/uncertainty.py
routing_stack/planning/orchestrator.py
```

검증:

```powershell
python -m pytest routing_stack\planning\tests routing_stack\context\tests -q
```

### Phase 4. viewer conversation payload

구현:

```text
routing_stack/viewer/app.js
routing_stack/viewer/styles.css
```

검증:

```powershell
node --check routing_stack\viewer\app.js
```

### Phase 5. 실험 도구와 문서

구현:

```text
routing_stack/experiments/router_compare.py
routing_stack/experiments/orchestrator_eval.py
README.md
```

검증:

```powershell
python -m routing_stack.experiments.router_compare "다음 코드를 분석해줘" --include_orchestrator
```

## 18. 회귀 기준

다음 케이스는 구현 후 반드시 확인한다.

```text
1. "이모티콘좀 그만 써라"
   Fast -> cheap

2. "안녕?"
   Fast -> cheap

3. "다음 코드를 분석해줘" + conversation에 코드 있음
   context_features.missing_context=false

4. "다음 코드를 분석해줘" + conversation 없음
   context_features.missing_context=true
   orchestrator -> abstain

5. "나의 설계의 부족한 부분을 찾아줘" + session_state.current_target 있음
   has_resolved_reference=true
   task 성격은 architecture/design review로 해석

6. previous_cheap_failure=true
   Fast/Balanced에서 cheap 선택 억제
```

## 19. 비범위

이번 설계에서 하지 않는 것:

- 외부 LLM planner 호출
- 웹 검색 기반 context resolution
- 파일 원문 파싱 전체 구현
- 이미지/PDF vision encoder 구현
- private simulator 전용 hard-coded prompt 규칙
- 라우터가 직접 답변을 생성하는 구조

## 20. 최종 판단

이 설계가 구현되면 현재 시스템은 다음 수준으로 올라간다.

```text
Prompt Router
  현재 문장만 보고 모델 선택

Task Router
  현재 문장 + 대화 상태 + 참조 대상 + 실행 이력 기반으로 모델 선택
```

가장 중요한 변화는 `missing_context`를 거부 규칙에서 해석 가능한 상태 신호로 바꾸는 것이다. `다음 코드를 분석해줘` 같은 요청은 더 이상 문장 패턴만으로 막지 않고, 실제 참조 대상이 있는지 확인한 뒤 라우팅한다.
