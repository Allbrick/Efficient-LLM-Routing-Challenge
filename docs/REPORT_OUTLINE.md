# 2026 오픈소스 개발자대회 결과보고서 초안

이 문서는 5페이지 이내 결과보고서 본문에 넣을 내용을 압축한 원본이다. 실제 HWPX/DOCX 작성 시 회색 안내 문구는 삭제하고, 아래 내용을 맑은고딕 10pt 기준으로 재배치한다.

## 1. 프로젝트 개요

| 항목 | 내용 |
| --- | --- |
| 프로젝트명 | Efficient LLM Routing Challenge |
| 프로젝트 등록 URL | GitHub 공개 저장소 URL로 교체 |
| 시연영상 | YouTube URL로 교체 |
| 한 줄 소개 | 사용자의 프롬프트, 예산 tier, 호출 이력, 모델 비용 metadata를 분석해 `cheap`, `mid`, `premium`, `abstain`, `select_output` 중 적절한 action을 선택하는 로컬 LLM 라우터 |

핵심 메시지:

```text
쉬운 요청은 저렴한 모델로 처리하고, 어려운 요청만 상위 모델로 승급해 LLM 운영 비용과 품질의 균형을 맞추는 오픈소스 라우팅 엔진이다.
```

## 2. 개발배경 및 목적

LLM 서비스에서 모든 요청을 가장 비싼 모델로 보내면 품질은 안정적이지만 비용과 컴퓨팅 자원이 낭비된다. 반대로 지나치게 저렴한 모델만 사용하면 코딩, 시스템 설계, 법률적 판단처럼 고난도 또는 고위험 요청에서 품질이 급격히 떨어진다.

본 프로젝트의 목적은 예산 tier별로 비용 민감도를 다르게 적용하면서, 각 프롬프트에 대해 “충분한 품질을 내는 가장 저렴한 action”을 선택하는 것이다. 특히 Fast/Balanced 저예산 환경에서 premium 호출을 억제하고, 정보가 부족한 요청은 무리하게 답변하지 않고 `abstain` 또는 기존 output 선택으로 처리하는 것을 목표로 한다.

## 3. 개발환경

- OS: Windows 개발 환경
- 언어: Python
- 주요 라이브러리: pandas, numpy, scikit-learn, lightgbm, joblib, pytest
- 라이선스: Apache License 2.0
- 실행 구조: `viewer -> router -> ai`
- AI backend: mock backend 또는 선택적 Ollama 로컬 모델
- 결과 자산: `docs/report_assets/*.csv`, `docs/report_assets/report_assets_summary.json`

## 4. 시스템 구성 및 아키텍처

```text
Prompt / Budget Tier / History / Model Metadata
        ↓
Input Normalizer / Context Resolver
        ↓
Router Adapter
        ↓
Geometric Router
        ↓
call_model / select_output / abstain
        ↓
Local AI Backend 또는 Private Simulator
```

주요 모듈:

- `routing_stack/`: viewer, router server, adapter, AI backend를 포함하는 공통 실행 스택
- `router_impls/geometric/router.py`: 예산 aware geometric router 본체
- `router_impls/geometric/submission.py`: private simulator 친화 adapter
- `router_impls/geometric/evaluator.py`: task별 deterministic evaluator
- `routing_stack/input/semantic_features.py`: optional semantic centroid feature
- `scripts/generate_report_assets.py`: 결과보고서용 수치와 표 자동 생성
- `data/external/dataset_sources.json`: 외부 공개 데이터/모델 출처와 라이선스 manifest

## 5. 주요 기능 및 기술

### 5.1 Budget-aware Routing

Fast, Balanced, Premium tier별로 비용 제한과 품질 목표를 다르게 적용한다. Fast에서는 premium 호출을 강하게 제한하고, Balanced는 비용과 품질 균형을, Premium은 품질 안정성을 더 우선한다.

### 5.2 Evaluator 기반 Success Label

단순 주관 점수만 사용하지 않고 다음 평가 규칙으로 후보 output의 성공 여부를 계산한다.

- `exact_match`
- `numeric_check`, `numeric_count`
- `unit_test`
- `exact_json`
- `constraint_check`
- `rubric_check`
- `required_clarification`
- `refusal_check`

이를 통해 프롬프트별 `expected_min_model`을 만들고, 라우터가 cheapest sufficient model을 학습하도록 한다.

### 5.3 History와 Model Metadata 활용

private simulator 입력에 포함되는 `history`와 `model_metadata`를 버리지 않고 활용한다. 이미 충분한 output이 history에 있으면 새 모델을 호출하지 않고 `select_output`을 반환한다. 요청별 모델 비용 metadata가 제공되면 해당 비용을 request-local cost로 반영한다.

### 5.4 Optional Public AI/Data 활용

기본 제출 경로는 외부 모델 없이 deterministic hash feature로 동작한다. 선택적으로 `intfloat/multilingual-e5-small` 같은 공개 임베딩 모델을 feature extractor로 사용할 수 있으며, 이 경우에도 파인튜닝이나 가중치 재배포 없이 centroid distance feature만 artifact에 저장한다.

외부 데이터는 RouteLLM, LMSYS, PRM800K, 한국어 instruction 데이터셋 등을 라우팅 평가 schema로 변환할 수 있도록 manifest와 import/filter/build 스크립트를 제공한다.

## 6. 구동 및 시연

설치:

```powershell
pip install -r requirements.txt
```

학습 및 정책 리포트 생성:

```powershell
python router_impls\geometric\scripts\train_geometric_router.py --policy_report artifacts\geometric_policy_report.json
```

보고서 자산 생성:

```powershell
python scripts\generate_report_assets.py --output_dir docs\report_assets
```

테스트:

```powershell
python -m pytest routing_stack\app\tests routing_stack\adapters\tests routing_stack\input\tests routing_stack\training\tests router_impls\geometric\tests -q
```

서버/뷰어 실행:

```powershell
python routing_stack\app\router_server.py --ai mock --port 4100
python routing_stack\app\viewer_server.py --router_server_url http://127.0.0.1:4100 --port 4010
```

## 7. 성능 근거

현재 공개 평가셋 기준 보고서 자산은 `docs/report_assets/`에 저장된다.

| Tier | Mean Quality | Mean Cost | Under-route | Weighted Score |
| --- | ---: | ---: | ---: | ---: |
| Fast | 0.889 | 0.048 | 11/73 | 0.131 |
| Balanced | 0.926 | 0.098 | 0/73 | 0.216 |
| Premium | 0.926 | 0.100 | 0/73 | 0.179 |

추가 근거:

- Overall weighted score: 0.526
- Fast batch allocation: total budget 2.19, total cost 2.18, mean cost 0.030
- 로컬 라우팅 decision latency: Fast 평균 7.26ms, Balanced 평균 7.18ms, Premium 평균 7.19ms
- 테스트 결과: 관련 테스트 70개 이상 통과

## 8. 기대효과 및 활용분야

- AI 서비스 운영 비용 절감
- 사내 AI gateway의 모델 선택 정책 엔진
- 로컬 LLM orchestration 연구/교육 플랫폼
- 폐쇄망/온디바이스 환경의 외부 API 없는 라우팅 시스템
- 모델별 비용이 다른 기업 환경에서 request-local cost 기반 최적화

## 9. 혁신성 및 차별성

- 단순 키워드 라우터가 아니라 evaluator 기반 success label과 sufficiency risk를 결합한다.
- `call_model`, `select_output`, `abstain`을 모두 지원해 중복 호출과 불필요한 고비용 호출을 줄인다.
- `model_metadata`를 반영해 private simulator나 실제 서비스의 모델 비용 변화에 대응한다.
- 외부 API 호출 없이 재현 가능한 오픈소스 구조를 유지하면서, 공개 데이터와 공개 임베딩 모델을 선택적으로 활용할 수 있다.
- 결과보고서용 수치와 demo prompt를 자동 생성해 성능 근거를 재현 가능하게 관리한다.

## 10. 한계점 및 향후 로드맵

현재 한계:

- public 예제 데이터 규모가 아직 작다.
- Fast tier에서 비용을 더 낮추면 under-route가 증가하는 trade-off가 남아 있다.
- 외부 공개 데이터셋은 manifest와 변환 파이프라인 중심이며, 대량 데이터 확보와 수동 검증은 제출 전 추가로 필요하다.

향후 발전:

- RouteLLM/LMSYS/PRM800K/한국어 instruction 데이터를 300개 이상 라우팅 평가셋으로 확장
- semantic feature를 공개 임베딩 모델 기반으로 검증
- before/after 리포트를 더 큰 holdout set에서 생성
- viewer에 history 기반 `select_output` 시나리오 추가
- latency 측정과 tie-break 지표 추가

## 11. 붙임 자료 연결

- 붙임1 SBOM 원본: `docs/SBOM.md`
- 붙임2 AI 모델 활용 명세 원본: `docs/AI_MODEL_USAGE.md`
- 시연 스크립트: `docs/DEMO_SCRIPT.md`
- 제출 체크리스트: `docs/SUBMISSION.md`
