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

라우터 서버는 기본적으로 `geometric`, `quality_utility`, `orchestrator`, `learned_label`을 모두 로드합니다. 뷰어에서 라우터를 선택해 같은 입력을 다른 라우터로 실행할 수 있습니다.

`orchestrator`는 답변을 생성하는 AI가 아니라, 내부적으로 base router 결과를 비교해 최종 모델을 고르는 planning 라우터입니다.

```powershell
python routing_stack\app\router_server.py --routers geometric,quality_utility,orchestrator --ai ollama --port 4100
python routing_stack\app\viewer_server.py --router_server_url http://127.0.0.1:4100 --port 4010
```

orchestrator만 서버에 노출하고 싶다면 다음처럼 실행할 수 있습니다.

```powershell
python routing_stack\app\router_server.py --routers orchestrator --default_router orchestrator --ai mock --port 4100
```

## Prompt/routing_score 기반 라우터 학습

`data/router_labels/prompt_labels.csv`에 `prompt,routing_score` 형식으로 예시를 추가하면 로컬 회귀 라우터를 다시 학습할 수 있습니다. `routing_score`는 0-100 범위의 모델 필요도 점수입니다.

- `0-40`: cheap
- `41-70`: mid
- `71-100`: premium

```csv
prompt,routing_score
안녕,8
FooDB와 BarQueue를 언제 각각 선택하는 것이 좋은가?,55
XAlgo를 구현하고 시간복잡도를 증명해줘,86
```

학습 명령:

```powershell
python -m routing_stack.training.train_prompt_label_router --csv data\router_labels\prompt_labels.csv --output artifacts\prompt_label_router.joblib
```

실행:

```powershell
python routing_stack\app\router_server.py --routers learned_label,orchestrator --default_router learned_label --ai mock --port 4100
```

이 라우터는 word/char TF-IDF와 공통 text feature를 함께 사용해 유사한 작업 유형으로 일반화합니다. 추가로 학습 feature 공간에서 `cheap`, `mid`, `premium` score 구간별 중심점 거리와 최근접 학습 예시를 계산하는 geometric memory를 사용합니다. 따라서 완전히 같은 학습 프롬프트는 사용자가 준 score를 우선하고, 새로운 프롬프트는 회귀 예측값과 geometric similarity를 함께 반영합니다.

viewer 오른쪽의 `CSV/TXT 평가·학습` 패널에서도 같은 구조의 CSV 또는 TXT를 업로드할 수 있습니다.

- `정답 비교`: 현재 선택한 라우터와 tier로 업로드 파일의 `routing_score`를 평가합니다. bucket accuracy와 MAE를 함께 표시합니다.
- `학습`: 업로드한 CSV/TXT로 `artifacts/prompt_label_router.joblib`를 다시 만들고 `learned_label` 라우터를 갱신합니다.

TXT 파일도 아래처럼 CSV와 같은 쉼표 구분 구조라면 그대로 사용할 수 있습니다.

```text
prompt,routing_score
안녕,8
React Context와 Zustand를 언제 각각 사용하는 것이 좋은가?,55
```

## Optional semantic features

geometric router는 기본적으로 구조적 feature와 deterministic hash text feature만 사용합니다. 공개 임베딩 모델을 활용하고 싶을 때는 semantic feature index를 별도 생성해 cheap/mid/premium centroid 거리와 uncertainty feature를 추가할 수 있습니다.

외부 모델 없이 재현 가능한 기본 index 생성:

```powershell
python scripts\build_semantic_feature_index.py --input data\public\example_eval_specs.csv --output artifacts\semantic_feature_index.json
```

geometric router 학습에 semantic feature 포함:

```powershell
python router_impls\geometric\scripts\train_geometric_router.py --semantic_features
```

`sentence-transformers`가 설치된 환경에서는 `intfloat/multilingual-e5-small` 같은 공개 임베딩 모델을 그대로 사용할 수 있습니다.

```powershell
python scripts\build_semantic_feature_index.py --input data\public\example_eval_specs.csv --output artifacts\semantic_feature_index.json --encoder sentence-transformers --model intfloat/multilingual-e5-small
```

## Geometric policy tuning report

geometric router 학습 스크립트는 튜닝된 정책과 평가 지표를 `artifacts/geometric_policy_report.json`에 저장합니다.

```powershell
python router_impls\geometric\scripts\train_geometric_router.py --policy_report artifacts\geometric_policy_report.json
```

리포트에는 tier별 `mean_quality`, `mean_cost`, `under_route`, `over_route`, `cost_over_limit`와 함께 다음 weighted objective가 포함됩니다.

```text
score_tier = quality - cost penalty - overflow penalty - under-route penalty - over-route penalty - abstain penalty
overall_score = 0.5 * fast + 0.3 * balanced + 0.2 * premium
```

## Report assets

결과보고서와 시연 영상에 넣을 표는 아래 명령으로 재생성합니다.

```powershell
python scripts\generate_report_assets.py --output_dir docs\report_assets
```

라우터 decision latency 리포트는 아래 명령으로 재생성합니다.

```powershell
python scripts\measure_router_latency.py --output_dir docs\report_assets --repeat 3
```

제출 전 필수 파일과 placeholder 상태는 아래 명령으로 확인합니다.

```powershell
python scripts\verify_submission_readiness.py --output docs\report_assets\submission_readiness.json
```

학습, 보고서 자산 생성, latency 측정, readiness 확인을 한 번에 실행하려면 다음 명령을 사용합니다.

```powershell
python scripts\run_submission_checks.py --output docs\report_assets\submission_check_run.json
```

주요 산출물:

- `docs/report_assets/tier_summary.csv`: tier별 품질, 비용, 오류, weighted score
- `docs/report_assets/before_after.csv`: 튜닝 전후 비용/품질 비교
- `docs/report_assets/selection_distribution.csv`: tier별 cheap/mid/premium/abstain 선택 분포
- `docs/report_assets/error_summary.csv`: under-route, over-route, should_abstain 분포
- `docs/report_assets/demo_prompts.csv`: 시연 영상용 대표 프롬프트
- `docs/report_assets/report_assets_summary.json`: 위 내용을 묶은 보고서용 JSON
- `docs/report_assets/latency_summary.csv`: tier별 로컬 라우팅 decision latency 요약
- `docs/report_assets/latency_report.json`: latency 측정 JSON 리포트
- `docs/report_assets/submission_readiness.json`: 제출 전 필수 파일과 URL placeholder 점검 결과
- `docs/report_assets/submission_check_run.json`: 제출 전 재현 명령 실행 결과

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
python -m pytest routing_stack\app\tests routing_stack\input\tests routing_stack\context\tests routing_stack\planning\tests routing_stack\adapters\tests routing_stack\training\tests routing_stack\experiments\tests router_impls\geometric\tests -q
```


