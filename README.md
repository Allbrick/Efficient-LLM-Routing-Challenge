# Efficient LLM Routing Challenge

이 저장소는 LLM 라우팅을 실험하는 프로젝트입니다. 실행 구조는 다음 3단계로 고정합니다.

```text
viewer -> router -> ai
```

`routing_stack/viewer`와 `routing_stack/ai`는 항상 동일하게 유지하고, 중간의 adapter만 교체합니다.

## 구조

- `routing_stack/`: 공통 `viewer -> router -> ai` 실행 스택
- `routing_stack/app/`: 공통 서버와 앱 조립 계층
- `routing_stack/viewer/`: 공통 UI와 HTTP API 서버
- `routing_stack/input/`: 입력 정규화와 router feature 추출 계층
- `routing_stack/context/`: 최근 대화, 세션 상태, 참조 대상을 task feature로 해석하는 계층
- `routing_stack/adapters/`: 교체 가능한 router adapter와 공통 router 계약
- `routing_stack/ai/`: `cheap`, `mid`, `premium`을 실행하는 공통 로컬 AI 계층
- `routing_stack/planning/`: 여러 라우터 결과를 종합하는 uncertainty/orchestrator 계층
- `routing_stack/experiments/`: 라우터 비교와 public set 근사 평가 도구
- `router_impls/geometric/`: geometric router 구현체
- `router_impls/quality_utility/`: quality-utility baseline router 구현체
- `data/public/`: 공개 예제 데이터
- `artifacts/`: geometric router 학습 산출물
- `docs/ROUTING_STACK_RULES.md`: 공통 스택 규칙

## 입력 정규화

라우터는 원본 파일이나 이미지를 직접 보지 않고, 정규화된 입력과 feature만 받습니다. 현재 구조는 단일 프롬프트뿐 아니라 최근 대화와 세션 상태를 함께 해석하는 Task Router 구조를 지원합니다.

```text
Text input
File input
Image input
PDF input
        ↓
Input Normalizer
        ↓
Context Resolver
        ↓
Router Feature Vector
        ↓
Router
```

현재 구현된 입력은 `text`입니다. 이후 파일, 이미지, PDF를 추가할 때도 router adapter 계약은 유지하고 `routing_stack/input/` 안에서 정규화 계층만 확장합니다.

## Task Router Context

`routing_stack/context/`는 현재 프롬프트가 이전 대화나 artifact를 참조하는지 판단합니다.

예를 들어 `다음 코드를 분석해줘`는 문장만 보면 정보가 부족하지만, 이전 대화에 코드가 있으면 `missing_context=false`로 라우팅을 계속합니다. 반대로 참조 대상이 없으면 `missing_context=true`로 보고 premium 호출 대신 `abstain` 쪽으로 보냅니다.

```powershell
python -m routing_stack.experiments.router_compare "다음 코드를 분석해줘" --context_json examples/context/code_context.json --include_orchestrator --tiers fast
python -m routing_stack.experiments.router_compare "다음 코드를 분석해줘" --context_json examples/context/unresolved_reference.json --include_orchestrator --tiers premium
```

context payload의 핵심 필드는 다음과 같습니다.

- `conversation`: 최근 대화입니다. viewer는 최근 10개 메시지만 보냅니다.
- `session_state`: 현재 작업 대상, 요약, artifact, 이전 호출 이력입니다.
- `call_history`: 모델 호출 실패나 재시도 이력입니다.

## 빠른 시작

의존성을 설치합니다.

```powershell
pip install -r requirements.txt
```

라우터 서버를 먼저 실행합니다. 라우터 서버는 등록된 라우터를 모두 로드하고 AI 호출까지 담당합니다.

```powershell
python routing_stack\app\router_server.py --ai mock --port 4100
```

다른 터미널에서 뷰어 서버를 실행합니다.

```powershell
python routing_stack\app\viewer_server.py --router_server_url http://127.0.0.1:4100 --port 4010
```

브라우저에서 `http://127.0.0.1:4010/`에 접속합니다.

## 로컬 무료 AI 연결

Ollama를 설치하고 로컬 모델을 받은 뒤 같은 viewer를 Ollama와 함께 실행합니다.

```powershell
ollama pull qwen3:4b-instruct
ollama pull qwen3:8b
ollama pull qwen3:14b
python routing_stack\app\router_server.py --ai ollama --port 4100
```

로컬 모델이 느려서 `timeout`이 발생하면 timeout을 늘릴 수 있습니다.

```powershell
python routing_stack\app\router_server.py --ai ollama --ai_timeout 240 --port 4100
```

AI 계층의 기본 모델 매핑은 다음과 같습니다.

```text
cheap   -> qwen3:4b-instruct
mid     -> qwen3:8b
premium -> qwen3:14b
```

## 라우터 선택

라우터 서버는 기본적으로 `geometric`, `quality_utility`, `orchestrator`를 모두 로드합니다. 뷰어에서 라우터를 선택해 같은 입력을 다른 라우터로 실행할 수 있습니다.

`orchestrator`는 답변을 생성하는 AI가 아니라, 내부적으로 base router 결과를 비교해 최종 모델을 고르는 planning 라우터입니다.

```powershell
python routing_stack\app\router_server.py --routers geometric,quality_utility,orchestrator --ai ollama --port 4100
python routing_stack\app\viewer_server.py --router_server_url http://127.0.0.1:4100 --port 4010
```

orchestrator만 서버에 노출하고 싶다면 다음처럼 실행할 수 있습니다.

```powershell
python routing_stack\app\router_server.py --routers orchestrator --default_router orchestrator --ai mock --port 4100
```

## 라우터 품질 예측 비교

난이도 하나를 예측하는 대신 `quality(prompt, model)`을 모델별로 비교합니다.
다음 명령은 같은 프롬프트를 여러 라우터와 tier에 넣고, `cheap`, `mid`, `premium`별 품질 예측과 선택 결과를 JSON으로 출력합니다.

```powershell
python -m routing_stack.experiments.router_compare "이모티콘좀 그만 써라" --include_orchestrator
```

출력의 핵심 필드는 다음과 같습니다.

- `model_quality`: 라우터가 보는 모델별 품질 예측입니다.
- `model_utility`: 비용 패널티까지 반영한 선택 점수입니다.
- `selected_model_id`: 실제 선택된 모델입니다.
- `selection_reason`: 선택 이유입니다.
- `planning`: orchestrator가 사용한 uncertainty와 geometric signal입니다.
- `routing_context`: Task Router가 해석한 참조, context confidence, missing context 판단입니다.

## public set 근사 평가

private simulator를 대체하는 정식 평가는 아니지만, 공개 train 샘플에서 선택 모델의 공개 quality/cost를 lookup해 라우터별 경향을 볼 수 있습니다.

```powershell
python -m routing_stack.experiments.orchestrator_eval --tiers fast
```

context fixture를 주입해 task router 경향을 볼 수도 있습니다.

```powershell
python -m routing_stack.experiments.orchestrator_eval --tiers fast --context_fixture examples/context/design_context.json
```

## 테스트

```powershell
python -m pytest routing_stack\app\tests routing_stack\input\tests routing_stack\context\tests routing_stack\planning\tests routing_stack\adapters\tests routing_stack\experiments\tests router_impls\geometric\tests -q
```


