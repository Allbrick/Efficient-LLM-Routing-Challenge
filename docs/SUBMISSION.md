# 제출 체크리스트

## 제출 후보

현재 제출 후보는 `router_impls/geometric/`이다.

`router_impls/quality_utility/`는 비교와 회귀 검증용 baseline이며, 최종 제출 라우터의 핵심 로직은 `router_impls/geometric`에 둔다.

## 필수 제출 파일

대회 결과보고서 제출 시 다음 2개 파일이 필요하다.

- `2026 오픈소스 개발자대회 결과보고서_접수번호(팀명).docx` 또는 `.hwpx`
- 위 문서를 변환한 `.pdf`

작성 제약:

- 결과보고서 본문 5페이지 이내
- 맑은고딕 10pt
- 양식 여백 임의 변경 금지
- 안내용 회색 문구 삭제
- 붙임1 SBOM 필수
- 붙임2 AI 모델 활용 정보는 해당 시 작성

## 저장소 제출 근거 문서

- 결과보고서 초안: `docs/REPORT_OUTLINE.md`
- SBOM 원본: `docs/SBOM.md`
- AI 모델 활용 명세 원본: `docs/AI_MODEL_USAGE.md`
- 시연 영상 스크립트: `docs/DEMO_SCRIPT.md`
- 보고서용 수치/표: `docs/report_assets/`
- 라이선스: `LICENSE`

## 재현 명령

의존성 설치:

```powershell
pip install -r requirements.txt
```

geometric router 학습과 정책 리포트 생성:

```powershell
python router_impls\geometric\scripts\train_geometric_router.py --policy_report artifacts\geometric_policy_report.json
```

보고서 자산 생성:

```powershell
python scripts\generate_report_assets.py --output_dir docs\report_assets
python scripts\measure_router_latency.py --output_dir docs\report_assets --repeat 3
python scripts\verify_submission_readiness.py --output docs\report_assets\submission_readiness.json
python scripts\run_submission_checks.py --output docs\report_assets\submission_check_run.json
```

테스트:

```powershell
python -m pytest routing_stack\app\tests routing_stack\adapters\tests routing_stack\input\tests routing_stack\training\tests router_impls\geometric\tests -q
```

서버/뷰어:

```powershell
python routing_stack\app\router_server.py --ai mock --port 4100
python routing_stack\app\viewer_server.py --router_server_url http://127.0.0.1:4100 --port 4010
```

## 주요 진입점

- 학습: `router_impls/geometric/scripts/train_geometric_router.py`
- 단일 라우팅: `router_impls/geometric/scripts/route_geometric_prompt.py`
- 통합 CLI: `router_impls/geometric/scripts/run_geometric_router.py`
- public simulation: `router_impls/geometric/scripts/simulate_geometric_router.py`
- batch allocation: `router_impls/geometric/scripts/allocate_geometric_budget.py`
- report assets: `scripts/generate_report_assets.py`
- latency report: `scripts/measure_router_latency.py`
- readiness check: `scripts/verify_submission_readiness.py`
- reproducibility runner: `scripts/run_submission_checks.py`
- private adapter: `router_impls/geometric/submission.py`

## Private Simulator 인터페이스

```python
from router_impls.geometric.submission import create_router

router = create_router("artifacts/geometric_router.json")
decision = router.route(
    prompt=prompt,
    budget_tier=budget_tier,
    history=history,
    model_metadata=model_metadata,
)
```

`decision["action"]`은 다음 중 하나다.

- `{"type": "call_model", "model_id": "cheap|mid|premium"}`
- `{"type": "select_output", "model_id": "cheap|mid|premium", "history_index": 0}`
- `{"type": "abstain", "model_id": None}`

## AI 모델 활용 정보 기재 기준

기본 제출 경로:

- 외부 생성형 LLM 가중치를 파인튜닝하지 않음
- 라우터는 코드 기반 정책 artifact로 모델 선택 action만 반환
- 기본 semantic feature는 `hash-char-token-v1` deterministic encoder 사용
- 붙임2의 유형 1~3에는 해당 없음

선택 경로:

- `sentence-transformers --model intfloat/multilingual-e5-small` 옵션을 사용해 semantic feature index를 생성하면 유형 1로 기재
- 추가 학습 없음
- 가중치 재배포 없음
- artifact에는 centroid distance feature만 저장

## 제출 전 최종 확인

- GitHub 저장소 URL을 `docs/REPORT_OUTLINE.md`와 `docs/AI_MODEL_USAGE.md`에 실제 URL로 교체
- YouTube 시연 영상 URL 추가
- `docs/report_assets/`를 최신 결과로 재생성
- `latency_summary.csv`와 `latency_report.json` 재생성
- `submission_readiness.json`에서 blocker가 0개인지 확인
- `submission_check_run.json`에서 `status`가 `passed`인지 확인
- `docs/SBOM.md`의 라이브러리 버전과 `requirements.txt` 일치 확인
- `python -m pytest ...` 전체 통과 확인
- DOCX/HWPX와 PDF 파일명 규칙 확인
- 결과보고서 안내 문구와 회색 placeholder 삭제
