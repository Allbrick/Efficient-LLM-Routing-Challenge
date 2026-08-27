# Efficient LLM Routing Challenge

프롬프트의 난이도를 로컬에서 판단해 **예산을 넘지 않는 가장 저렴하고 충분한 모델**을 고르는 LLM 라우터입니다.

라우터는 답변을 생성하지 않습니다. 주어진 프롬프트와 예산 tier에 대해 `cheap` / `mid` / `premium` 호출, 기존 출력 재사용(`select_output`), 거절(`abstain`) 중 하나의 **결정만** 반환합니다.

- **GPU · API 키 · 네트워크 불필요** — CPU 단독으로 동작합니다
- 학습 artifact(`artifacts/geometric_router.json`)가 저장소에 포함되어 clean clone 직후 바로 실행됩니다
- 요구사항은 **Python 3.12 이상**뿐입니다

---

## Quick Start

```powershell
git clone https://github.com/Allbrick/Efficient-LLM-Routing-Challenge
cd Efficient-LLM-Routing-Challenge
pip install -r requirements.txt
python scripts\demo.py
```

`demo.py`는 환경 점검 → 테스트 → public set 시뮬레이션 → 시연 시나리오를 순서대로 실행합니다.
테스트를 건너뛰려면 `--skip-test`를 붙입니다.

### 하위 명령

| 명령 | 용도 |
| --- | --- |
| `python scripts\demo.py doctor` | 환경 / 의존성 / artifact / 진입점 점검 |
| `python scripts\demo.py route "<프롬프트>" --tier fast` | 프롬프트 하나를 라우팅하고 근거 출력 |
| `python scripts\demo.py showcase` | 핵심 강점 시나리오 6종 시연 |
| `python scripts\demo.py sim` | public set 시뮬레이션 + tier별 요약 |
| `python scripts\demo.py viewer` | 브라우저 시연 (서버 2개 자동 기동) |
| `python scripts\demo.py full` | 학습부터 제출 검증까지 전체 재현 |

---

## 단일 프롬프트 라우팅

```powershell
python scripts\demo.py route "2 + 3은 얼마야?" --tier fast
```

```text
  프롬프트   : 2 + 3은 얼마야?
  예산 tier  : fast
  결정       : call_model -> cheap
  선택 근거  : simple_prompt_prior
  pre-route  : cheap_direct (obvious_low_risk_prompt)

    model        cost  dist/rad    pass    suff  feasible
    abstain     0.000      0.00   0.247   0.247  no
    cheap       0.010      1.85   0.296   0.294  no
    mid         0.050      2.13   0.645   0.556  no
    premium     0.200     18.94   0.802   0.753  no
```

| 항목 | 의미 |
| --- | --- |
| `dist/rad` | 학습된 success envelope 중심으로부터의 정규화 거리 (작을수록 그 모델이 성공해 온 영역) |
| `pass` / `suff` | 모델별 통과 확률과 충분성 확률 |
| `feasible` | 현재 tier의 예산 feasible region 안에 드는지 |

같은 프롬프트라도 tier에 따라 결정이 달라집니다.

```powershell
python scripts\demo.py route "마이크로서비스 전환 전략을 설계해줘" --tier fast     # 예산 제약으로 제한
python scripts\demo.py route "마이크로서비스 전환 전략을 설계해줘" --tier premium  # 다른 feasible region
```

---

## 채점 시뮬레이터 연동

진입점은 한 곳입니다.

```python
from router_impls.geometric.submission import create_router

router = create_router()          # artifacts/geometric_router.json 자동 탐색
decision = router.route(
    prompt=prompt,
    budget_tier=budget_tier,      # "fast" | "balanced" | "premium"
    history=history,
    model_metadata=model_metadata,
)
```

`decision["action"]`은 다음 중 하나입니다.

```python
{"type": "call_model",    "model_id": "cheap|mid|premium"}
{"type": "select_output", "model_id": "cheap|mid|premium", "history_index": 0}
{"type": "abstain",       "model_id": None}
```

호출자의 작업 디렉터리와 무관하게 artifact를 자동 탐색하며, 내부 오류가 나도 예외를 던지지 않고 `cheap` 호출로 degrade합니다.

---

## 동작 원리

```text
Prompt / Budget Tier / History / Model Metadata
    -> Input Normalizer / Context Resolver
    -> Geometric Router
    -> call_model / select_output / abstain
```

1. **Geometric Success Envelope** — cheap / mid / premium이 실제로 성공했던 프롬프트 분포를 중심과 반경을 가진 envelope으로 학습하고, 새 프롬프트까지의 정규화 거리로 판정합니다.
2. **Budget Feasible Region** — 요청별 예산이 hard constraint입니다. 한도를 넘는 모델은 어떤 경우에도 호출하지 않습니다.
3. **4-Lane Pre-Route** — `missing_context`(참조 대상 부재) / `cheap_direct` / `hard_task` / `ambiguous`로 먼저 분기합니다. `hard_task`는 tier별 모델 하한을 적용하되, 비싼 모델이 충분성에서 뚜렷하게 앞서지 못하면 하한을 내립니다.
4. **Repetition-Invariant Geometry** — 반복 입력은 표면 길이가 아니라 압축된 의미 길이로 판정합니다.

---

## 성능

public evaluation set 73건 기준입니다. 전체 weighted score는 `0.251`입니다.

| Tier | 예산 | 평균 품질 | 평균 비용 | 예산 초과 | 평균 지연 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fast | 0.03 | 0.688 | 0.008 | **0/73** | 23.72ms |
| Balanced | 0.08 | 0.857 | 0.030 | **0/73** | 24.26ms |
| Premium | 0.20 | 0.931 | 0.106 | **0/73** | 23.34ms |

baseline 대비:

| 정책 | Fast 품질 | Fast 예산초과 | Balanced 품질 | Premium 품질 |
| --- | ---: | ---: | ---: | ---: |
| always_cheap | 0.565 | 0/73 | 0.565 | 0.565 |
| always_mid | 0.805 | **73/73** | 0.805 | 0.805 |
| always_premium | 0.808 | **73/73** | 0.808 | 0.808 |
| **geometric (제출)** | 0.688 | **0/73** | **0.857** | **0.931** |

`always_mid`와 `always_premium`은 Fast tier에서 73건 전부 예산을 초과하므로 유효한 정책이 아닙니다. geometric router는 **예산을 한 번도 넘지 않으면서** 예산이 열리는 tier에서 always_premium을 넘어섭니다.

수치는 전부 `docs/report_assets/`에 스크립트로 생성됩니다.

| 확인 항목 | 파일 |
| --- | --- |
| 프롬프트별 라우팅 근거 | `docs/report_assets/geometric_explanations.csv` |
| baseline 대비 비교 | `docs/report_assets/router_comparison.csv` |
| 충분성 확률 보정 (Brier / ECE) | `docs/report_assets/sufficiency_calibration_summary.json` |
| tier별 요약 | `docs/report_assets/tier_summary.csv` |
| 전체 재현 검증 결과 | `docs/report_assets/submission_check_run.json` |

---

## 브라우저 시연

```powershell
python scripts\demo.py viewer
```

`router_server`와 `viewer_server`를 자동 기동합니다. 기본값이 `--ai mock`이라 **Ollama 없이도 라우팅 결정 전체를 시연**할 수 있습니다. `Ctrl+C`로 두 서버 모두 정리됩니다.

선택된 모델의 실제 응답까지 보려면 로컬 Ollama를 연결합니다.

```powershell
ollama pull qwen3:4b-instruct   # cheap
ollama pull qwen3:8b            # mid
ollama pull qwen3:14b           # premium
python scripts\demo.py viewer --ai ollama
```

옵션: `--router-port`(기본 4100), `--viewer-port`(기본 4010), `--no-browser`

---

## 전체 재현

```powershell
python scripts\demo.py full
```

라우터 학습 → report asset 생성 → baseline/preset 비교 → calibration 리포트 → latency 측정 → pytest → 제출 검증을 순차 실행합니다.

개별 실행:

```powershell
python router_impls\geometric\scripts\train_geometric_router.py
python scripts\run_submission_checks.py --full
python -m pytest -q
```

---

## 저장소 구조

| 경로 | 내용 |
| --- | --- |
| `router_impls/geometric/` | 제출 라우터 구현체 (`submission.py`가 진입점) |
| `router_impls/quality_utility/` | 비교용 baseline 라우터 |
| `routing_stack/` | 공통 `viewer -> router -> ai` 실행 스택 |
| `routing_stack/adapters/` | 교체 가능한 router adapter와 공통 계약 |
| `routing_stack/input/`, `context/` | 입력 정규화와 컨텍스트 해석 계층 |
| `scripts/` | 학습 · 리포트 생성 · 검증 스크립트 |
| `data/public/` | 공개 예제 데이터 |
| `artifacts/` | 학습 산출물 (제출 artifact 포함) |
| `docs/report_assets/` | 스크립트로 생성한 성능 근거 |

---

## 문제 해결

| 증상 | 조치 |
| --- | --- |
| `학습 artifact 없음` | `python scripts\demo.py full`로 재생성 |
| 패키지 미설치 경고 | `pip install -r requirements.txt` |
| viewer 포트 충돌 | `--router-port` / `--viewer-port`로 변경 |
| `--ai ollama`에서 응답 없음 | Ollama 실행 여부와 모델 3개 다운로드 확인, 또는 `--ai mock` 사용 |
| 한글이 깨져 보임 | `chcp 65001` 실행 후 재시도 |

---

## 라이선스

Apache License 2.0 — 자세한 내용은 `LICENSE`를 참고하세요.

의존성은 pandas, numpy, scikit-learn, lightgbm, scipy, joblib, pytest 7개이며 전부 MIT/BSD 계열입니다. 제출 라우터의 실행 경로에서는 외부 API를 호출하지 않습니다.
