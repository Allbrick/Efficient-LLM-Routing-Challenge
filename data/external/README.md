# External Routing Data Sources

이 폴더는 외부 공개 데이터셋을 라우팅 학습/평가 포맷으로 변환할 때 필요한 출처, 라이선스, 필터링 정책을 관리한다.

원칙:

- 원본 대용량 데이터셋 전체를 저장소에 재배포하지 않는다.
- 변환된 샘플은 `source`, `license`, `source_url`을 함께 보존한다.
- 개인정보, 민감정보, 저작권 문제가 될 수 있는 장문 원문은 필터링한다.
- 라우터 학습에는 생성형 LLM 가중치가 아니라 `prompt -> expected_min_model` 및 `success` 성격의 라벨만 사용한다.
- 외부 데이터 없이도 기존 프로젝트 테스트와 라우터 실행은 동작해야 한다.

권장 변환 schema:

```csv
source,prompt_id,prompt,language,task_type,difficulty,risk_level,evaluation_type,expected_min_model,label_confidence,license,source_url
```

파일:

- `dataset_sources.json`: 외부 데이터셋/모델 출처와 라이선스 manifest
- `routing_prompts.csv`: 필터링된 외부 prompt 샘플
- `external_eval_specs.csv`: `data/public/example_eval_specs.csv`와 호환되는 외부 평가 명세
- `routing_labels.csv`: 라우팅 라벨 변환 결과
- `filter_report.json`: 필터링 결과 통계
- `external_dataset_summary.json`: source/license/expected_min_model 분포 요약

현재는 manifest, 필터링 도구, 한국어 instruction importer, Hugging Face dataset viewer API 기반 샘플 downloader, 평가 명세 builder를 제공한다. 원본 데이터셋 전체는 저장소에 재배포하지 않고 필터링된 prompt 샘플과 출처 metadata만 보존한다.

## Download public samples

아래 명령은 무료 공개 데이터셋에서 작은 샘플을 내려받아 바로 routing schema로 변환하고 PII/길이 필터를 적용한다.

```powershell
python scripts\download_public_dataset_samples.py --ko_limit 320 --mt_bench_limit 180
```

현재 생성된 샘플 요약:

```text
routing_prompts.csv: 329 rows
CarrotAI ko-instruction: 311 rows
LMSYS MT-Bench human judgments: 18 rows
Korean prompts: 311 rows
English prompts: 18 rows
```

다운로드 요약은 `external_download_summary.json`에 저장된다.

## Korean instruction import

Hugging Face 등에서 한국어 instruction 데이터셋을 CSV 또는 JSONL로 내려받은 뒤 로컬 파일을 입력으로 변환한다.

```powershell
python scripts\import_korean_instruction.py --input data\external\raw_ko_instruction.csv --output data\external\routing_prompts.csv --report data\external\filter_report.json
```

지원 입력 필드:

- `prompt`
- `instruction`
- `question`
- `query`
- `text`
- `input`
- `context`
- `source_text`
- `conversations`
- `messages`

변환 과정:

- prompt를 라우팅 schema로 정규화한다.
- source/license/source_url은 `dataset_sources.json`에서 보강한다.
- 개인정보 가능성이 있는 row를 제거한다.
- task_type, difficulty, risk_level, evaluation_type, expected_min_model은 보수적 heuristic으로 초기 라벨링한다.

주의:

- importer가 만든 라벨은 초기 약지도 라벨이다.
- 최종 제출 데이터에는 sampling review 또는 evaluator 기반 검증을 추가해야 한다.

## Build external eval specs

필터링된 `routing_prompts.csv`를 기존 평가 파이프라인에서 읽을 수 있는 평가 명세 CSV로 변환한다.

```powershell
python scripts\build_external_routing_dataset.py --input data\external\routing_prompts.csv --output data\external\external_eval_specs.csv --summary data\external\external_dataset_summary.json
```

출력 schema는 `data/public/example_eval_specs.csv`와 동일하다.

```csv
prompt_id,prompt,task_type,difficulty,risk_level,expected_min_model,evaluation_type,reference_answer,test_spec
```

`test_spec`에는 외부 데이터 출처 검증을 위해 다음 metadata를 JSON으로 보존한다.

- `source`
- `license`
- `source_url`
- `label_confidence`

`external_dataset_summary.json`은 source, license, expected_min_model, difficulty, risk_level, evaluation_type 분포를 기록한다. 결과보고서에는 이 요약을 이용해 외부 공개 데이터가 어떤 방식으로 라우팅 평가셋에 반영됐는지 설명한다.

## Optional semantic feature index

외부 prompt 라벨을 cheap/mid/premium semantic centroid로 압축해 라우터 feature로 사용할 수 있다. 기본 encoder는 deterministic hash encoder라 외부 모델 다운로드 없이 동작한다.

```powershell
python scripts\build_semantic_feature_index.py --input data\external\external_eval_specs.csv --output artifacts\semantic_feature_index.json
```

`sentence-transformers`가 설치된 환경에서는 공개 임베딩 모델을 그대로 사용할 수 있다.

```powershell
python scripts\build_semantic_feature_index.py --input data\external\external_eval_specs.csv --output artifacts\semantic_feature_index.json --encoder sentence-transformers --model intfloat/multilingual-e5-small
```

geometric router 학습에 semantic feature를 포함하려면 다음 옵션을 사용한다.

```powershell
python router_impls\geometric\scripts\train_geometric_router.py --semantic_features
```
