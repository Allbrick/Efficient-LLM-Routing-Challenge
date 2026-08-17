# SBOM

이 문서는 결과보고서 붙임1에 기재할 소프트웨어 자재명세서 원본이다.

| 번호 | 라이브러리명 | 버전 | 라이선스 | 공식 저장소 URL | 사용 목적 및 주요 기능 |
| ---: | --- | --- | --- | --- | --- |
| 1 | pandas | 3.0.3 | BSD-3-Clause | https://github.com/pandas-dev/pandas | 공개 라우팅 데이터 CSV 로딩, 평가 결과 집계, 시뮬레이션 리포트 생성 |
| 2 | numpy | 2.4.6 | BSD-3-Clause | https://github.com/numpy/numpy | 프롬프트 feature vector, 거리 계산, 확률/점수 연산 |
| 3 | pytest | 9.0.3 | MIT | https://github.com/pytest-dev/pytest | 라우터, evaluator, adapter, training utility 테스트 실행 |
| 4 | lightgbm | 4.6.0 | MIT | https://github.com/microsoft/LightGBM | quality-utility baseline의 품질 예측 모델 학습 및 비교 실험 |
| 5 | scikit-learn | 1.9.0 | BSD-3-Clause | https://github.com/scikit-learn/scikit-learn | prompt label router 학습, TF-IDF/회귀 모델, 비교 baseline 구축 |
| 6 | joblib | 1.5.3 | BSD-3-Clause | https://github.com/joblib/joblib | 학습된 prompt label router artifact 저장 및 로딩 |
| 7 | sentence-transformers | 선택 설치 | Apache-2.0 | https://github.com/UKPLab/sentence-transformers | 선택적 공개 임베딩 모델 feature 생성. 기본 제출 경로에서는 설치하지 않아도 동작 |

## 비고

- 본 프로젝트의 핵심 제출 라우터는 `router_impls/geometric`이며, 외부 LLM API를 실시간 호출하지 않는다.
- `routing_stack/ai`의 Ollama 연동은 선택적 로컬 시연 backend이다.
- 기본 제출 경로는 `requirements.txt`의 필수 패키지만으로 테스트와 라우터 실행이 가능하다.
- `sentence-transformers`는 `scripts/build_semantic_feature_index.py --encoder sentence-transformers`를 사용할 때만 필요한 선택 의존성이다.
- 선택적으로 `intfloat/multilingual-e5-small`을 사용할 경우, 모델 자체의 라이선스와 출처는 `docs/AI_MODEL_USAGE.md`와 `data/external/dataset_sources.json`에 함께 기록한다.
