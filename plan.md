# Task Router 전환 계획

이 문서는 현재 `prompt router` 구조를 `task router`로 한 단계 확장하기 위한 실행 계획입니다. 목표는 단일 프롬프트 문자열만 보고 모델을 고르는 한계를 줄이고, 현재 요청이 참조하는 대화 상태, 첨부 대상, 이전 실행 결과, 비용 제약을 함께 고려하는 로컬 라우팅 구조를 만드는 것입니다.

프로젝트 범위는 `PROJECT.md`를 따른다.

- 라우터는 외부 API나 네트워크 서비스를 호출하지 않는다.
- 라우터는 답변을 직접 생성하지 않는다.
- 최종 선택은 후보 모델 호출 또는 기존 후보 출력 선택이다.
- Fast / Balanced / Premium tier의 비용-품질 trade-off를 유지한다.
- 저예산 tier에서 불필요한 premium 선택을 줄이는 것을 우선한다.

## 1. 문제 정의

현재 구조는 다음 흐름이다.

```text
현재 프롬프트
  ↓
Input Normalizer
  ↓
prompt feature
  ↓
geometric / quality_utility / orchestrator
  ↓
selected model
```

이 구조는 다음 요청에서 취약하다.

```text
이거 수정해줘.
나의 설계의 부족한 부분을 찾아줘.
다음 코드를 분석해줘.
아까 말한 방식으로 구현해줘.
```

이런 요청은 현재 문장만 보면 짧고 쉬워 보이지만, 실제 난이도는 이전 대화, 참조 대상, 첨부 코드, 파일 크기, 요구 출력 수준에 의해 결정된다. 따라서 라우터의 판단 단위를 `prompt`가 아니라 `task context`로 올려야 한다.

## 2. 목표 구조

목표 구조는 다음과 같다.

```text
viewer
  ↓
router_server
  ↓
Input Normalizer
  ↓
Context Resolver
  ├─ 현재 요청
  ├─ 최근 대화
  ├─ 세션 상태 요약
  ├─ 참조 대상
  ├─ 첨부/파일 feature
  └─ 이전 호출 이력
  ↓
Task Feature Package
  ↓
geometric / quality_utility
  ↓
uncertainty
  ↓
orchestrator
  ↓
selected model
  ↓
LocalAI
```

라우터와 실행 모델에 주는 컨텍스트는 분리한다.

```text
Context Resolver
  ├─ router_context: 라우터가 볼 압축 feature
  └─ executor_context: AI가 답변 생성에 사용할 상세 context
```

초기 구현에서는 `executor_context`를 실제 AI 프롬프트에 강하게 붙이기보다, 먼저 `router_context`를 안정적으로 만들고 라우터 선택 정확도를 개선한다.

## 3. 핵심 설계 원칙

### 3.1 최근 N개 메시지보다 의존성 경계를 우선한다

최근 6개 메시지만 보는 방식은 단순하지만 위험하다. 설계나 코드가 20턴 전에 정의됐을 수 있기 때문이다.

판단 기준은 다음과 같다.

- 현재 요청의 대상이 무엇인지 식별됐는가
- 최신 상태를 재구성할 수 있는가
- 평가 기준과 제약 조건을 알 수 있는가
- 참조 대상이 없어서 모델을 호출해도 실패할 가능성이 높은가

### 3.2 라우터에는 원문 전체가 아니라 압축 feature를 준다

라우터에 전체 대화 원문을 넣으면 비용과 지연이 늘고, 챌린지 조건에도 맞지 않는다. 라우터는 다음과 같은 feature를 받는다.

```json
{
  "requires_cross_turn_reasoning": true,
  "context_token_estimate": 8500,
  "has_reference_expression": true,
  "has_resolved_reference": true,
  "has_attached_code": true,
  "missing_context": false,
  "expected_output_complexity": 0.62,
  "retry_count": 1,
  "previous_failure": false
}
```

### 3.3 “missing context”는 거부 장치가 아니라 판단 신호로 바꾼다

기존에는 `다음 코드를 분석해줘` 같은 문장이 코드 없이 들어오면 `missing_context`로 보고 abstain하거나 사실상 거부하는 흐름이 강했다.

Task Router에서는 이를 다음처럼 바꾼다.

```text
참조 표현 있음
  ↓
Context Resolver가 참조 대상 검색
  ├─ 최근 대화/세션 상태/첨부에서 대상 발견
  │   └─ missing_context=false, 라우팅 계속
  └─ 대상 없음
      └─ missing_context=true, clarification 또는 abstain
```

즉, `다음 코드`라는 표현 자체를 거부 근거로 쓰지 않는다. 실제로 참조할 코드가 없을 때만 `missing_context=true`로 본다.

## 4. 추가할 모듈

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

### 4.1 types.py

역할:

- task context 관련 dataclass 정의

예상 타입:

```python
@dataclass(frozen=True)
class ConversationMessage:
    role: str
    content: str
    created_at: str | None = None


@dataclass(frozen=True)
class SessionState:
    summary: str = ""
    current_target: str = ""
    constraints: dict[str, Any] = field(default_factory=dict)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    previous_calls: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class RoutingContext:
    current_prompt: str
    recent_messages: list[ConversationMessage]
    session_state: SessionState
    router_context: dict[str, Any]
    executor_context: dict[str, Any]
    context_confidence: float
```

### 4.2 reference_detector.py

역할:

- 현재 요청이 이전 대화나 첨부 대상을 참조하는지 감지

감지 대상:

- `이거`, `그거`, `아까`, `방금`, `위 내용`, `다음 코드`, `첨부한 파일`
- `나의 설계`, `현재 구조`, `이 구조`, `방금 말한 방식`
- `이전 결과`, `다시`, `수정해줘`, `보완해줘`

출력 예:

```json
{
  "has_reference_expression": true,
  "reference_types": ["prior_context", "code_or_artifact"],
  "needs_resolution": true
}
```

### 4.3 state_summary.py

역할:

- 세션 상태 요약을 구조화한다.
- 현재는 외부 LLM 없이 payload로 받은 summary를 정규화하고 feature화한다.
- 이후 viewer가 대화 상태를 서버에 보낼 수 있게 되면 이 모듈이 상태를 누적한다.

초기 구현 범위:

- `session_state.summary`
- `session_state.current_target`
- `session_state.constraints`
- `session_state.artifacts`
- `session_state.previous_calls`

라우터가 직접 긴 요약을 읽지 않도록 다음 feature를 만든다.

```text
state_summary_length
state_summary_token_estimate
has_current_target
constraint_count
artifact_count
previous_call_count
previous_failure_count
```

### 4.4 context_features.py

역할:

- 현재 프롬프트 feature와 context feature를 합친다.

초기 feature:

```text
requires_cross_turn_reasoning
has_reference_expression
has_resolved_reference
missing_context
context_confidence
context_token_estimate
conversation_message_count
artifact_count
attached_code_count
attached_file_count
previous_call_count
previous_failure_count
retry_count
output_format_constraint_count
tool_requirement_count
```

비용 관련 feature:

```text
estimated_total_input_tokens
estimated_total_output_tokens
context_token_pressure
history_token_pressure
artifact_token_pressure
```

### 4.5 resolver.py

역할:

- payload에서 현재 요청, 최근 대화, 세션 상태를 받아 `RoutingContext`를 만든다.

초기 입력 payload 예:

```json
{
  "prompt": "다음 코드를 분석해줘",
  "conversation": [
    {"role": "user", "content": "아래 코드야..."}
  ],
  "session_state": {
    "summary": "사용자는 라우터 설계를 개선 중이다.",
    "current_target": "Efficient LLM Routing Challenge task router 설계",
    "artifacts": [
      {"type": "code", "name": "router_server.py", "token_estimate": 1200}
    ]
  },
  "call_history": []
}
```

초기 출력:

```json
{
  "current_prompt": "다음 코드를 분석해줘",
  "router_context": {
    "has_reference_expression": true,
    "has_resolved_reference": true,
    "missing_context": false,
    "requires_cross_turn_reasoning": true,
    "context_token_estimate": 1400
  },
  "executor_context": {
    "summary": "...",
    "resolved_references": [...]
  },
  "context_confidence": 0.86
}
```

## 5. 기존 구조 변경 계획

### 5.1 RouteRequest 확장

현재:

```python
RouteRequest(
    prompt: str,
    tier: str,
    input_features: dict
)
```

변경:

```python
RouteRequest(
    prompt: str,
    tier: str,
    input_features: dict,
    context_features: dict,
    executor_context: dict,
    call_history: list
)
```

호환성을 위해 새 필드는 기본값을 둔다.

### 5.2 router_server.py 변경

현재:

```text
payload
  ↓
normalize_input()
  ↓
RouteRequest
```

변경:

```text
payload
  ↓
normalize_input()
  ↓
resolve_context()
  ↓
RouteRequest(input_features + context_features)
```

초기에는 기존 viewer가 conversation/session_state를 보내지 않아도 동작해야 한다.

### 5.3 viewer 변경

초기 범위:

- 현재 채팅 transcript를 `/api/route` payload의 `conversation`으로 보낸다.
- 새 대화 버튼을 누르면 conversation도 초기화한다.
- 라우팅 상세에 `context_confidence`, `missing_context`, `has_resolved_reference`를 표시한다.

주의:

- viewer는 모든 과거 대화를 무한히 보내지 않는다.
- 초기 구현에서는 최근 10개 메시지만 보낸다.
- 장기 상태 요약은 다음 단계에서 추가한다.

### 5.4 Input Normalizer와의 관계

`routing_stack/input/`은 단일 입력 정규화 책임을 유지한다.

`routing_stack/context/`는 여러 입력과 세션 상태를 조합하는 책임을 갖는다.

```text
input/   = 현재 입력을 feature화
context/ = 현재 입력이 속한 작업 상태를 feature화
```

## 6. missing_context 정책 변경

### 6.1 현재 문제

다음 문장은 단독으로 보면 정보가 부족하다.

```text
다음 코드를 분석해줘
이거 수정해줘
나의 설계를 검토해줘
```

하지만 실제로는 이전 대화나 첨부 파일에 대상이 있을 수 있다. 기존처럼 문장 패턴만 보고 `missing_context=true`로 두면 유효한 작업을 잘못 거부한다.

### 6.2 변경 정책

`missing_context`를 다음 3단계로 나눈다.

```text
reference_detected
reference_resolved
missing_context
```

판단 규칙:

```text
reference_detected=false
  => missing_context=false

reference_detected=true and reference_resolved=true
  => missing_context=false

reference_detected=true and reference_resolved=false
  => missing_context=true
```

### 6.3 라우터 적용

Fast tier:

- 참조가 해결됐고 context가 작으면 cheap 또는 mid도 허용
- 참조가 해결됐지만 context가 크고 코드/파일 분석이면 mid 우선
- 참조가 해결되지 않으면 abstain

Balanced tier:

- 참조가 해결됐으면 task feature 기반으로 품질-비용 비교
- 참조가 해결되지 않으면 abstain 또는 clarification

Premium tier:

- 참조가 해결됐고 정확도 요구가 높으면 premium 허용
- 참조가 해결되지 않았다는 이유만으로 premium을 호출하지 않는다

## 7. 구현 단계

### Phase 1. Context 타입과 참조 감지

파일:

```text
routing_stack/context/types.py
routing_stack/context/reference_detector.py
routing_stack/context/tests/test_reference_detector.py
```

완료 기준:

- `이거`, `다음 코드`, `나의 설계`, `아까 말한 방식` 감지
- 참조 유형을 `prior_context`, `artifact`, `design`, `code` 등으로 분류
- 외부 호출 없이 deterministic 동작

### Phase 2. Context feature 생성

파일:

```text
routing_stack/context/context_features.py
routing_stack/context/state_summary.py
routing_stack/context/tests/test_context_features.py
```

완료 기준:

- recent conversation, session_state, artifacts, call_history에서 feature 추출
- `context_token_estimate`, `artifact_count`, `previous_failure_count` 생성
- 기존 `input_features`와 충돌하지 않는 key prefix 또는 명확한 naming 사용

### Phase 3. Context Resolver 구현

파일:

```text
routing_stack/context/resolver.py
routing_stack/context/tests/test_resolver.py
```

완료 기준:

- payload에서 `conversation`, `session_state`, `call_history`를 읽는다.
- 참조 표현이 있고 관련 conversation/artifact가 있으면 `has_resolved_reference=true`
- 참조 표현만 있고 대상이 없으면 `missing_context=true`
- `RoutingContext.to_dict()` 제공

### Phase 4. RouteRequest와 router_server 연결

파일:

```text
routing_stack/adapters/contract.py
routing_stack/app/router_server.py
routing_stack/app/tests/test_routing_stack.py
```

완료 기준:

- 기존 payload는 그대로 동작
- 새 payload의 context 정보가 `RouteRequest`에 포함
- 서버 응답의 `input`에 `routing_context` 포함
- 기존 테스트 깨지지 않음

### Phase 5. 기존 missing_context 로직 조정

파일 후보:

```text
routing_stack/input/text_features.py
routing_stack/input/normalizer.py
routing_stack/planning/uncertainty.py
routing_stack/planning/orchestrator.py
router_impls/geometric/
```

작업:

- 단일 문장 패턴 기반 `missing_context`를 약화한다.
- context resolver의 `reference_resolved` 결과를 우선한다.
- `다음 코드를 분석해줘`는 참조 대상이 있으면 거부하지 않는다.
- 참조 대상이 없을 때만 `abstain` 또는 clarification 성격의 선택으로 보낸다.

완료 기준:

```text
prompt="다음 코드를 분석해줘", conversation에 코드 있음
  => missing_context=false

prompt="다음 코드를 분석해줘", conversation 비어 있음
  => missing_context=true

prompt="이모티콘좀 그만 써라"
  => simple_directive=true, cheap 유지
```

### Phase 6. orchestrator 정책 확장

파일:

```text
routing_stack/planning/uncertainty.py
routing_stack/planning/orchestrator.py
routing_stack/planning/tests/
```

추가 신호:

```text
requires_cross_turn_reasoning
context_token_pressure
has_resolved_reference
previous_failure
retry_count
artifact_token_pressure
```

정책:

- 참조가 해결된 짧은 작업은 cheap/mid 허용
- 참조가 해결된 코드/설계 리뷰는 mid 이상 선호
- 이전 cheap 실패가 있으면 mid 또는 premium 승급
- missing context는 premium 호출 대신 abstain

### Phase 7. viewer conversation payload 적용

파일:

```text
routing_stack/viewer/app.js
routing_stack/viewer/styles.css
```

작업:

- transcript 기반 최근 대화 배열 유지
- `/api/route` 요청에 `conversation` 포함
- 응답에서 `routing_context` 요약 표시

완료 기준:

- 일반 채팅 UX 유지
- 새 대화 시 conversation 초기화
- 라우팅 상세에서 context 판단 결과 확인 가능

### Phase 8. 실험 도구 확장

파일:

```text
routing_stack/experiments/router_compare.py
routing_stack/experiments/orchestrator_eval.py
```

작업:

- `--conversation_json` 또는 `--context_json` 옵션 추가
- 단일 prompt 평가와 task context 평가를 분리해 출력
- missing context 케이스 회귀 테스트 추가

예:

```powershell
python -m routing_stack.experiments.router_compare "다음 코드를 분석해줘" --context_json examples/context/code_context.json --include_orchestrator
```

### Phase 9. 문서 갱신

파일:

```text
README.md
docs/
```

작업:

- prompt router와 task router 차이 설명
- context payload 예시 추가
- missing_context 정책 변경 설명
- 로컬 챌린지 제약과의 관계 명시

## 8. 테스트 계획

### 단위 테스트

- 참조 표현 감지 테스트
- context feature 생성 테스트
- resolver의 missing/resolved 판단 테스트
- `RouteRequest` 하위 호환성 테스트
- orchestrator tier별 정책 테스트

### 통합 테스트

```powershell
python -m pytest routing_stack\context\tests routing_stack\planning\tests routing_stack\app\tests -q
```

### 회귀 테스트

반드시 유지할 케이스:

```text
이모티콘좀 그만 써라
  => Fast에서 cheap

안녕?
  => Fast에서 cheap

다음 코드를 분석해줘 + 이전 대화에 코드 있음
  => missing_context=false

다음 코드를 분석해줘 + 이전 대화 없음
  => missing_context=true 또는 abstain

나의 설계의 부족한 부분을 찾아줘 + session_state.current_target 있음
  => architecture_review task로 인식
```

## 9. 리스크

### 9.1 context feature가 prompt feature보다 과도하게 강해질 수 있음

대응:

- 초기에는 context feature를 보조 신호로만 사용한다.
- Fast tier premium 승급 조건은 계속 엄격하게 둔다.

### 9.2 viewer가 대화 전체를 계속 보내면 payload가 커질 수 있음

대응:

- 초기에는 최근 10개 메시지만 전송한다.
- 장기 상태는 `session_state.summary`로 분리한다.

### 9.3 missing_context 완화로 잘못된 모델 호출이 늘 수 있음

대응:

- `reference_detected`와 `reference_resolved`를 분리한다.
- 참조가 해결되지 않으면 premium을 호출하지 않는다.
- resolved confidence가 낮으면 uncertainty를 높인다.

### 9.4 챌린지 private simulator와 실제 viewer context가 다를 수 있음

대응:

- context 필드는 모두 optional로 둔다.
- private simulator가 prompt만 제공해도 기존 라우터가 동작해야 한다.
- context feature가 없을 때는 현재 prompt router 경로로 fallback한다.

## 10. 성공 기준

1. 기존 단일 프롬프트 라우팅이 깨지지 않는다.
2. `conversation`, `session_state`, `call_history`가 있으면 라우터 feature에 반영된다.
3. `다음 코드를 분석해줘` 같은 참조형 요청을 문장 패턴만으로 거부하지 않는다.
4. 참조 대상이 실제로 없을 때는 `missing_context=true`로 판단한다.
5. orchestrator가 context 기반 uncertainty를 설명할 수 있다.
6. Fast tier에서 단순 요청은 계속 cheap을 선택한다.
7. 모든 로직은 로컬 코드로 재현 가능하다.

## 11. 권장 구현 순서 요약

1. `routing_stack/context/` 추가
2. 참조 표현 감지기 구현
3. context feature 생성기 구현
4. resolver 구현
5. `RouteRequest`와 `router_server` 연결
6. missing_context 정책 조정
7. orchestrator uncertainty 정책 확장
8. viewer conversation payload 추가
9. 실험 도구와 README 갱신
10. 회귀 테스트 실행
