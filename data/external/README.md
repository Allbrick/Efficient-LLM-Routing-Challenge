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
- `routing_labels.csv`: 라우팅 라벨 변환 결과
- `filter_report.json`: 필터링 결과 통계

현재는 manifest와 필터링 도구만 제공한다. 실제 외부 데이터 다운로드는 대회 제출 전 라이선스를 재확인한 뒤 별도 절차로 수행한다.
