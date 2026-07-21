# Geometric Router 하드 설정 제거 계획

## 목적

현재 `geometric_router`는 제출 가능한 구조에 가까워졌지만, 일부 판단이 수동 threshold, prior, public 데이터 의존, 문자열 규칙에 묶여 있다. 이 문서는 해당 하드 설정을 제거하거나 public 분석용과 private 제출용으로 분리하기 위한 실행 계획이다.

목표는 다음과 같다.

- private simulator에서 사용할 수 없는 정보 제거
- 데이터 기반 calibration으로 threshold 대체
- public 분석 도구와 제출 router 분리
- evaluator 규칙을 코드가 아니라 schema와 검증기로 이동
- classifier 오류가 전체 routing 실패로 전파되는 구조 완화

## 현재 하드 설정 목록

### 1. Abstain 강제 prior

위치:

- `geometric_router/router.py`

현재 구조:

```python
if evaluation_type in {"required_clarification", "refusal_check"}:
    abstain_probability = max(abstain_probability, 0.85)
```

문제:

- classifier가 `evaluation_type`을 잘못 예측하면 바로 abstain 오판으로 이어진다.
- `0.85`는 데이터에서 학습된 값이 아니라 수동값이다.
- abstain을 action으로 분리한 것은 맞지만, action 확률은 아직 충분히 학습 기반이 아니다.

제거 방향:

- `AbstainCalibrator`를 별도 모델로 만든다.
- 입력은 `risk_model`의 abstain 확률, task classifier confidence, missing context evidence, evaluation type distribution.
- 출력은 calibrated `P(abstain | prompt, tier)`.
- 수동 `0.85` prior는 제거하고 artifact에 저장된 calibration table 또는 logistic score를 사용한다.

완료 기준:

- `required_clarification`, `refusal_check` 샘플에서 abstain recall 측정
- non-abstain 샘플에서 abstain false positive 측정
- hard-coded `0.85` 제거

## 2. 수동 threshold와 radius multiplier

위치:

- `geometric_router/router.py`

현재 구조:

```python
DEFAULT_PASS_THRESHOLDS = {
    "fast": 0.74,
    "balanced": 0.82,
    "premium": 0.90,
}

DEFAULT_ABSTAIN_THRESHOLDS = {
    "fast": 0.55,
    "balanced": 0.55,
    "premium": 0.55,
}

DEFAULT_RADIUS_MULTIPLIERS = {
    "fast": {"cheap": 1.10, "mid": 1.10, "premium": 1.10},
    ...
}
```

문제:

- 데이터셋 크기와 분포가 바뀌면 threshold가 바로 낡는다.
- `tune_geometric_policy.py`의 loss가 현재 allocator objective와 다르다.
- Fast/ Balanced/ Premium별 threshold가 실제 budget objective에서 최적인지 검증되지 않았다.

제거 방향:

- public train을 train/calibration split으로 나눈다.
- 각 tier별 목적 함수를 정의한다.
  - under-route penalty
  - over-route cost penalty
  - abstain false positive penalty
  - budget excess penalty
  - quality loss
- grid/random search로 threshold와 radius multiplier를 calibration set에서 선택한다.
- 선택된 값은 코드 상수가 아니라 `artifacts/geometric_router.json`의 `policy`에 저장한다.

완료 기준:

- `DEFAULT_*` 값은 fallback으로만 남긴다.
- 기본 학습 명령이 calibration 결과를 artifact에 저장한다.
- `tune_geometric_policy.py`와 allocator objective가 동일한 loss를 사용한다.

## 3. Budget limit 고정

위치:

- `geometric_router/router.py`

현재 구조:

```python
BUDGET_LIMITS = {
    "fast": 0.03,
    "balanced": 0.08,
    "premium": 0.20,
}
```

문제:

- 공식 simulator 예산이 다르면 전체 allocation이 틀어진다.
- 코드 상수라 실험별 budget 변경이 어렵다.

제거 방향:

- `RouterConfig` 또는 `policy_config.json` 도입
- budget limits를 artifact metadata에 저장
- CLI에서 `--budget_config` 또는 `--fast_budget` 같은 인자를 받는다.
- private simulator가 budget metadata를 제공하면 adapter에서 주입한다.

완료 기준:

- router core가 전역 `BUDGET_LIMITS`에 직접 의존하지 않는다.
- simulation/allocation/viewer가 동일 config를 읽는다.

## 4. Public actual_quality 사용 분리

위치:

- `geometric_router/budget_allocator.py`

현재 구조:

```python
if "actual_quality" in option:
    return 0.70 * float(option["actual_quality"]) + 0.30 * probability_quality
```

문제:

- public 분석에서는 유용하지만 private에서는 선택 전 실제 품질을 모른다.
- 제출용 allocator에 들어가면 data leakage에 가까운 구조가 된다.

분리 방향:

- `analysis_allocator.py`와 `submission_allocator.py`로 역할 분리
- public 분석용:
  - actual quality 사용 가능
  - oracle lower bound 계산 가능
  - viewer 표시용
- private 제출용:
  - pass probability
  - sufficiency probability
  - predicted expected quality
  - cost
  - risk priority
  - history
  만 사용

완료 기준:

- `RouterSubmission` 경로에서는 actual quality를 절대 참조하지 않는다.
- public viewer는 분석용 allocator를 명시적으로 사용한다.
- README에 두 allocator의 역할이 분리되어 있다.

## 5. Feature extractor의 규칙 기반 추론

위치:

- `geometric_router/features.py`

현재 역할:

- difficulty score 추론
- risk score 추론
- missing context 추론
- exact answer 추론
- code-like/task hint 추론

문제:

- 길이, 조건 수, 특정 힌트 기반 추론은 데이터가 다양해지면 불안정하다.
- 한국어/영어 표현 변화에 취약하다.
- classifier와 중복되는 판단이 있다.

제거/축소 방향:

- `EvidenceExtractor`는 순수 구조 feature만 남긴다.
  - 길이
  - 줄 수
  - 숫자/JSON/code block 존재
  - 조건/구분자 수
  - 입력 누락 패턴 여부
- difficulty/risk/evaluation type은 `TaskClassifier`와 calibration 모델이 담당한다.
- `_infer_difficulty`, `_infer_risk`는 fallback으로만 사용하고 기본 route에서는 classifier 출력 사용.

완료 기준:

- prompt text keyword에 의존하는 risk/difficulty 결정 비중 감소
- feature extractor output과 classifier output이 명확히 분리
- feature ablation test 추가

## 6. Rubric evaluator의 문자열 포함 방식

위치:

- `geometric_router/evaluator.py`

현재 구조:

- `required_terms`
- `required_concepts`
- `relations`
- `forbidden_claims`
- `critical_failures`

문제:

- 개념이 실제로 설명됐는지보다 문자열 포함 여부에 가깝다.
- 동의어는 schema에 넣어야 하므로 spec 작성 부담이 크다.
- 키워드 나열 답변이 높은 점수를 받을 수 있다.

개선 방향:

- rubric schema를 더 구조화한다.
  - `required_concepts`
  - `required_relations`
  - `required_sections`
  - `forbidden_claims`
  - `critical_failures`
  - `minimum_explanation_units`
- relation 검증 강화
  - 단순 window 기반이 아니라 anchor/action/object 관계를 검사
- section 검증 추가
  - 제목 또는 JSON field 기준
- evaluator 결과에 concept별 pass/fail details를 반환

완료 기준:

- 단순 키워드 나열 출력이 rubric_check를 통과하지 못하는 테스트 추가
- relation 없는 언급과 관계 설명을 구분
- evaluator details가 labels/debug artifact에 저장됨

## 7. Synthetic data 자동 주입

위치:

- `geometric_router/router.py`

현재 구조:

```python
if include_synthetic:
    synthetic_train, synthetic_specs = build_numeric_count_data()
```

문제:

- numeric_count를 보강하는 데는 좋지만 데이터 비율이 작을 때 router가 특정 쉬운 문제 유형을 과대 학습할 수 있다.
- synthetic과 real public data의 weight가 동일하다.

개선 방향:

- synthetic row에 `sample_weight` 추가
- fit 단계에서 sample weighting 지원
- synthetic category별 비율 제한
- 최종 제출 artifact metadata에 synthetic 사용 여부와 weight 기록

완료 기준:

- `include_synthetic` 기본값을 config에서 제어
- synthetic 가중치를 0, 0.25, 0.5, 1.0로 sweep 가능
- numeric_count 성능과 일반 성능 tradeoff 리포트 생성

## 8. Task classifier confidence calibration

위치:

- `geometric_router/task_classifier.py`

문제:

- `field_confidence`는 score normalization일 뿐 실제 정확도와 calibration되어 있지 않다.
- classifier가 evaluation type을 틀리면 abstain, risk, threshold 선택까지 연쇄 오류가 난다.

개선 방향:

- calibration split에서 confidence bin별 accuracy 측정
- field별 reliability table 저장
- low confidence일 때:
  - risk를 보수적으로 올림
  - abstain direct prior는 낮춤
  - route reason에 `low_classifier_confidence` 추가

완료 기준:

- `classifier_calibration.json` 생성
- field별 ECE 또는 bin accuracy 리포트
- low confidence routing test 추가

## 실행 우선순위

### Phase 1. 제출 경로와 분석 경로 분리

1. `submission_allocator.py` 생성
2. `analysis_allocator.py` 또는 기존 `budget_allocator.py` 역할 명확화
3. `RouterSubmission`이 public actual quality에 접근하지 않는지 테스트
4. README 업데이트

결과:

- data leakage 리스크 제거

### Phase 2. Abstain prior 학습화

1. `AbstainCalibrator` 추가
2. `abstain_probability = max(..., 0.85)` 제거
3. required/refusal/non-abstain 검증셋에서 precision/recall 측정
4. viewer에 abstain probability breakdown 표시

결과:

- classifier 오분류에 대한 취약성 감소

### Phase 3. Threshold/radius calibration 통합

1. 현재 `tune_geometric_policy.py` loss 폐기 또는 갱신
2. allocator objective와 동일한 loss 사용
3. calibration split 기반 policy 저장
4. `--no_tune` 없이도 안정적인 artifact 생성

결과:

- 수동 threshold 의존도 감소

### Phase 4. Feature extractor 축소

1. keyword 기반 risk/difficulty fallback 분리
2. classifier 기반 metadata 예측을 기본값으로 사용
3. feature ablation test 추가

결과:

- prompt keyword 편향 감소

### Phase 5. Evaluator 고도화

1. rubric relation schema 강화
2. section/checklist details 반환
3. 키워드 나열 실패 테스트 추가

결과:

- 학습 라벨 신뢰도 상승

## 최종 완료 기준

다음 조건을 만족하면 하드 설정 제거 작업을 완료로 본다.

- 제출 adapter 경로에서 public `quality_score`를 참조하지 않는다.
- abstain 확률이 수동 `0.85` prior 없이 계산된다.
- pass/abstain threshold는 calibration artifact에서 읽는다.
- budget limit은 config 또는 simulator 입력으로 주입 가능하다.
- evaluator의 rubric check는 단순 키워드 나열을 통과시키지 않는다.
- task classifier confidence calibration 리포트가 존재한다.
- `python -m pytest tests -q`가 통과한다.
- `python scripts\run_geometric_router.py route ...`가 정상 동작한다.
