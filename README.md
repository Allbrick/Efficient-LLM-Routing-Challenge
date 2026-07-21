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
- `routing_stack/adapters/`: 교체 가능한 router adapter와 공통 router 계약
- `routing_stack/ai/`: `cheap`, `mid`, `premium`을 실행하는 공통 로컬 AI 계층
- `router_impls/geometric/`: geometric router 구현체
- `router_impls/quality_utility/`: quality-utility baseline router 구현체
- `data/public/`: 공개 예제 데이터
- `artifacts/`: geometric router 학습 산출물
- `docs/ROUTING_STACK_RULES.md`: 공통 스택 규칙

## 입력 정규화

라우터는 원본 파일이나 이미지를 직접 보지 않고, 정규화된 입력과 feature만 받습니다.

```text
Text input
File input
Image input
PDF input
        ↓
Input Normalizer
        ↓
Router Feature Vector
        ↓
Router
```

현재 구현된 입력은 `text`입니다. 이후 파일, 이미지, PDF를 추가할 때도 router adapter 계약은 유지하고 `routing_stack/input/` 안에서 정규화 계층만 확장합니다.

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

AI 계층의 기본 모델 매핑은 다음과 같습니다.

```text
cheap   -> qwen3:4b-instruct
mid     -> qwen3:8b
premium -> qwen3:14b
```

## 라우터 선택

라우터 서버는 기본적으로 `geometric`, `quality_utility`를 모두 로드합니다. 뷰어에서 라우터를 선택해 같은 입력을 다른 라우터로 실행할 수 있습니다.

```powershell
python routing_stack\app\router_server.py --routers geometric,quality_utility --ai ollama --port 4100
python routing_stack\app\viewer_server.py --router_server_url http://127.0.0.1:4100 --port 4010
```

## 라우터 품질 예측 비교

난이도 하나를 예측하는 대신 `quality(prompt, model)`을 모델별로 비교합니다.
다음 명령은 같은 프롬프트를 여러 라우터와 tier에 넣고, `cheap`, `mid`, `premium`별 품질 예측과 선택 결과를 JSON으로 출력합니다.

```powershell
python -m routing_stack.experiments.router_compare "이모티콘좀 그만 써라"
```

출력의 핵심 필드는 다음과 같습니다.

- `model_quality`: 라우터가 보는 모델별 품질 예측입니다.
- `model_utility`: 비용 패널티까지 반영한 선택 점수입니다.
- `selected_model_id`: 실제 선택된 모델입니다.
- `selection_reason`: 선택 이유입니다.

## 테스트

```powershell
python -m pytest routing_stack\app\tests routing_stack\input\tests routing_stack\experiments\tests router_impls\geometric\tests -q
```


