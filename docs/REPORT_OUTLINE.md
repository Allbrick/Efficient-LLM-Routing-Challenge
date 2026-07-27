# 2026 오픈소스 개발자대회 결과보고서 초안

이 문서는 5페이지 이내 결과보고서에 넣을 본문 초안이다. 실제 제출 파일에는 GitHub URL, YouTube URL, 접수번호를 최종 값으로 교체한다.

## 1. 프로젝트 개요

| 항목 | 내용 |
| --- | --- |
| 프로젝트명 | Efficient LLM Routing Challenge |
| 저장소 URL | GitHub 공개 저장소 URL로 교체 |
| 시연 영상 | YouTube URL로 교체 |
| 한 줄 소개 | 프롬프트를 geometric feature space에 배치하고 모델별 성공 envelope와 예산 tier별 feasible region을 결합해 `cheap`, `mid`, `premium`, `abstain`, `select_output` 중 최적 action을 고르는 로컬 LLM 라우터 |

핵심 메시지:

```text
이 라우터는 답변을 직접 생성하지 않는다. 로컬 feature 계산과 geometric artifact lookup만으로, 주어진 요청에 충분한 가장 저렴한 모델 또는 abstain/select_output action을 선택한다.
```

## 2. 개발 배경과 목적

모든 요청을 premium 모델로 보내면 품질은 안정적이지만 운영 비용이 커진다. 반대로 always cheap 정책은 쉬운 요청에는 효율적이지만 코드, 설계, 추론, 안전성 판단처럼 어려운 요청에서 실패한다.

본 프로젝트의 목적은 비용-품질 trade-off를 단순 키워드 규칙이 아니라 geometric decision problem으로 풀어내는 것이다. 프롬프트를 feature vector로 변환하고, cheap/mid/premium 모델이 성공했던 영역을 envelope로 학습한 뒤, 예산 tier별 feasible region 안에서 cheapest sufficient action을 선택한다.

## 3. 시스템 구조

```text
Prompt / Budget Tier / History / Model Metadata
        -> Input Normalizer / Context Resolver
        -> Geometric Router
        -> call_model / select_output / abstain
        -> Local AI Backend or Private Simulator
```

주요 모듈:

- `router_impls/geometric/router.py`: budget-aware geometric routing 정책
- `router_impls/geometric/features.py`: prompt를 geometric feature vector로 변환
- `router_impls/geometric/envelope.py`: 모델별 성공 영역 계산
- `router_impls/geometric/evaluator.py`: task별 deterministic 평가
- `router_impls/geometric/submission.py`: private simulator adapter
- `routing_stack/input/text_features.py`: 반복 압축과 입력 정규화 feature
- `scripts/generate_report_assets.py`: 제출 보고서용 기본 수치 생성
- `scripts/generate_geometric_explanations.py`: prompt별 geometric decision 근거 생성
- `scripts/generate_router_comparison.py`: always cheap/mid/premium baseline 비교
- `scripts/generate_policy_preset_comparison.py`: 운영 preset별 비용-품질 비교

## 4. 핵심 기술

### Geometric Success Envelope

각 prompt는 길이, 구조, 코드성, 위험도, task type, hash text feature 등으로 구성된 feature vector가 된다. 학습 단계에서는 모델별 성공 prompt 분포를 cheap/mid/premium envelope로 저장한다. 라우팅 단계에서는 새 prompt가 어떤 envelope 안에 있거나 가까운지, 각 모델의 pass probability가 충분한지 계산한다.

### Budget Feasible Region

Fast, Balanced, Premium tier는 같은 prompt에도 다른 선택 공간을 갖는다. Fast에서는 premium을 기본적으로 강하게 제한하고, hard/risk 신호가 있을 때만 예외적으로 허용한다. Balanced는 비용과 품질 균형을, Premium은 품질 안정성을 더 크게 본다.

### Repetition-Invariant Geometry

단순히 길다고 어려운 prompt로 보지 않기 위해 반복 입력을 별도로 다룬다. 예를 들어 “원피스 세계관에 대해 철학적 물음을 던져줘”를 여러 번 반복한 prompt는 의미 난이도가 증가한 것이 아니라 표면 노이즈가 증가한 것이다. 라우터는 반복 span을 압축한 semantic prompt로 핵심 feature를 계산하고, `repetition_ratio`, `compressed_length_norm`을 evidence로 남긴다.

이 처리는 억지 예외 규칙이 아니라 geometric 설계의 핵심을 보여준다. 의미 좌표와 표면 길이 좌표를 분리해야 cheap envelope 안에 있는 쉬운 요청을 premium으로 잘못 보내지 않는다.

## 5. 데이터와 학습

기본 제출 artifact는 저장소 내 public example set과 synthetic routing examples로 재현 가능하게 학습된다. 추가로 무료 공개 데이터셋을 라우팅 schema로 변환하는 경로를 제공한다.

현재 외부 데이터 경로:

- `CarrotAI/ko-instruction-dataset`: 한국어 instruction prompt 샘플 311개
- `lmsys/mt_bench_human_judgments`: MT-Bench human preference prompt 샘플 18개
- 변환 결과: `data/external/routing_prompts.csv`, `data/external/external_eval_specs.csv`
- 외부 약지도 artifact: `artifacts/geometric_router_external.json`

외부 데이터는 원본 대용량 dataset을 저장소에 재배포하지 않고, source/license/source_url metadata를 남긴 샘플과 weak expected_min_model label만 관리한다.

## 6. 성능 근거

현재 public evaluation 기반 수치:

| Tier | Mean Quality | Mean Cost | Cost Over Limit | Under-route | Weighted Score |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fast | 0.885 | 0.046 | 37/73 | 12/73 | 0.136 |
| Balanced | 0.926 | 0.097 | 33/73 | 0/73 | 0.217 |
| Premium | 0.926 | 0.099 | 0/73 | 0/73 | 0.179 |

전체 weighted score는 `0.532`이다. 로컬 decision latency는 Fast `7.94ms`, Balanced `7.90ms`, Premium `7.95ms` 수준이다.

Baseline 비교:

- always_cheap: Fast mean_quality `0.565`, under_route `36/73`
- always_mid: Fast mean_quality `0.805`, cost_over_limit `73/73`
- always_premium: Fast mean_quality `0.808`, cost_over_limit `73/73`
- geometric_tuned: Fast mean_quality `0.885`, cost_over_limit `37/73`, under_route `12/73`

즉 geometric router는 항상 싼 모델을 쓰는 정책보다 품질을 크게 높이고, 항상 비싼 모델을 쓰는 정책보다 비용 제약을 더 잘 반영한다.

## 7. 실행과 재현

```powershell
pip install -r requirements.txt
python scripts\run_submission_checks.py --full --output docs\report_assets\submission_check_run.json
```

개별 명령:

```powershell
python router_impls\geometric\scripts\train_geometric_router.py --policy_report artifacts\geometric_policy_report.json
python scripts\generate_report_assets.py --output_dir docs\report_assets
python scripts\generate_geometric_explanations.py --output_dir docs\report_assets
python scripts\generate_router_comparison.py --output_dir docs\report_assets
python scripts\generate_policy_preset_comparison.py --output_dir docs\report_assets
python scripts\measure_router_latency.py --output_dir docs\report_assets --repeat 3
python -m pytest routing_stack\app\tests routing_stack\adapters\tests routing_stack\input\tests routing_stack\training\tests router_impls\geometric\tests -q
```

## 8. 기대 효과와 활용 분야

- AI 서비스 운영 비용 절감
- 사내 AI gateway의 모델 선택 정책 엔진
- 로컬 LLM orchestration 연구/교육 플랫폼
- 모델별 비용이 다른 기업 환경에서 request-local cost 기반 최적화
- 제한된 예산 환경에서 품질 저하를 통제하는 라우팅 시스템

## 9. 한계와 향후 개선

현재 public dataset 규모는 아직 작고, private distribution과 완전히 같다고 보장할 수 없다. 외부 공개 데이터셋은 약지도 label 기반이므로 최종 제출 전 수동 검증과 holdout 평가를 더 늘릴 필요가 있다.

향후 개선 방향:

- RouteLLM/LMSYS/PRM800K 계열 데이터 확장
- semantic feature index를 공개 embedding 모델 기반으로 추가 검증
- history 기반 `select_output` scenario 확대
- model metadata 기반 request-local cost 반영 강화
- 반복, prompt injection, missing context edge case를 report asset으로 더 체계화

## 10. 첨부 자료

- SBOM: `docs/SBOM.md`
- AI 모델 사용 명세: `docs/AI_MODEL_USAGE.md`
- 시연 스크립트: `docs/DEMO_SCRIPT.md`
- 제출 체크리스트: `docs/SUBMISSION.md`
- 전략 문서: `docs/GEOMETRIC_SCORING_STRATEGY.md`
