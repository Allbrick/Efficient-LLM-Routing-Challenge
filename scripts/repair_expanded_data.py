from __future__ import annotations

from pathlib import Path

import pandas as pd


TRAIN_PATH = Path("data/public/example_train.csv")
SPEC_PATH = Path("data/public/example_eval_specs.csv")

EXPANDED_IDS = {
    "e501", "e502", "e503", "e504", "e505", "e506",
    "e601", "e602", "e603", "e604", "e605", "e606",
    "e701", "e702", "e703", "e704",
}


def main() -> None:
    train = pd.read_csv(TRAIN_PATH)
    specs = pd.read_csv(SPEC_PATH)
    train = train[~train["prompt_id"].isin(EXPANDED_IDS)].copy()
    specs = specs[~specs["prompt_id"].isin(EXPANDED_IDS)].copy()

    expanded_specs = build_specs()
    train_rows = []
    for spec in expanded_specs:
        train_rows.extend(build_train_rows(spec))

    train = pd.concat([train, pd.DataFrame(train_rows)], ignore_index=True)
    specs = pd.concat([specs, pd.DataFrame(expanded_specs)], ignore_index=True)
    train.to_csv(TRAIN_PATH, index=False, encoding="utf-8")
    specs.to_csv(SPEC_PATH, index=False, encoding="utf-8")
    print(f"repaired prompts: {len(expanded_specs)}")
    print(f"train rows: {len(train)}, specs rows: {len(specs)}")


def build_specs() -> list[dict]:
    apple_text = "사과 바나나 포도 사과 귤 " * 80
    log_text = "INFO ERROR DEBUG INFO ERROR WARN " * 70
    release_note = ("릴리즈 노트는 내일 오전 아홉 시에 공유됩니다. " * 30).strip()
    csv_items = ",".join(f"item{i}" for i in range(1, 61))
    trim_text = ("alpha beta gamma " * 40).strip()
    number_text = "1 7 2 7 3 4 7 5 6 7 " * 50

    return [
        spec("e501", f'다음 긴 문단에서 "사과"라는 단어가 몇 번 등장하는지만 숫자로 답해줘.\n\n{apple_text}', "numeric_count", "trivial", "low", "cheap", "numeric_count", "160", "count exact target occurrences"),
        spec("e502", f"아래 로그에서 ERROR가 몇 번 등장하는지만 숫자로 답하세요.\n\n{log_text}", "numeric_count", "trivial", "low", "cheap", "numeric_count", "140", "count exact target occurrences"),
        spec("e503", f"다음 문장을 그대로 한 번만 반복해줘.\n\n{release_note}", "copy_exact", "trivial", "low", "cheap", "exact_match", release_note, "exact copy without commentary"),
        spec("e504", f"다음 쉼표 구분 목록의 항목 개수만 숫자로 답해줘: {csv_items}", "numeric_count", "trivial", "low", "cheap", "numeric_count", "60", "count csv items"),
        spec("e505", f'다음 긴 문자열에서 앞뒤 공백만 제거하고 그대로 출력해줘: "   {trim_text}   "', "string_transform", "trivial", "low", "cheap", "exact_match", trim_text, "trim only"),
        spec("e506", f"다음 문단에서 숫자 7이 등장하는 횟수만 답해줘.\n\n{number_text}", "numeric_count", "trivial", "low", "cheap", "numeric_count", "200", "count numeric token occurrences"),
        spec("e601", "의료 예약 플랫폼의 개인정보 접근 제어를 설계해줘. 환자, 의사, 보험 담당자, 고객지원 담당자가 있고, 응급 접근, 사후 감사, 최소 권한, 데이터 마스킹, 동의 철회, 권한 위임, 이상 접근 탐지를 모두 포함해야 한다. 구성요소, 정책 모델, 감사 로그 스키마, 실패 시나리오를 구분해 설명해줘.", "security_architecture", "hard", "high", "premium", "rubric_check", "", "required=RBAC|ABAC|break-glass|audit log|least privilege|masking|consent revocation|delegation|anomaly detection|failure scenarios"),
        spec("e602", "은행 이체 시스템에서 중복 요청, 부분 실패, 원장 불일치, 재시도 폭주, 메시지 순서 뒤바뀜이 있어도 잔액 정합성을 지키는 설계를 해줘. idempotency key, double-entry ledger, outbox, reconciliation, retry backoff, dead letter queue, audit trail을 포함해줘.", "financial_consistency", "hard", "high", "premium", "rubric_check", "", "required=idempotency key|double-entry ledger|outbox|reconciliation|retry backoff|DLQ|audit trail|ordering|partial failure"),
        spec("e603", "TypeScript로 취소 가능한 제한 동시성 작업 큐를 설계하고 구현해줘. AbortSignal, concurrency limit, 작업 순서 보존, 실패 시 신규 작업 중단, 실행 중 작업 정리, timeout, 결과 타입 안전성을 모두 만족해야 한다.", "code_hard", "hard", "medium", "premium", "unit_test", "", "concurrency; AbortSignal; preserve order; stop new tasks on failure; timeout; type safety"),
        spec("e604", "멀티 리전 SaaS에서 테넌트별 데이터 레지던시를 보장하는 아키텍처를 설계해줘. 라우팅, 키 관리, 백업, 장애 조치, 감사, 데이터 삭제 요청, cross-region replication 금지 예외 처리를 포함해야 한다.", "architecture_constraints", "hard", "high", "premium", "rubric_check", "", "required=data residency|tenant routing|KMS|backup|failover|audit|deletion request|replication exception"),
        spec("e605", "대규모 이벤트 수집 파이프라인에서 exactly-once라고 주장하는 설계를 검토해줘. Kafka, consumer crash, offset commit, idempotent sink, dedup store, replay, backfill, late event를 고려해 실제 보장 가능한 수준과 불가능한 수준을 구분해줘.", "distributed_systems", "hard", "high", "premium", "rubric_check", "", "required=exactly-once limits|at-least-once|offset commit|idempotent sink|dedup store|replay|backfill|late event"),
        spec("e606", "권한 있는 내부자가 고객 데이터를 무단 조회하는 것을 탐지하고 대응하는 시스템을 설계해줘. 접근 정책, 행위 기반 이상 탐지, 근거 보존, 알림 피로도 감소, 사후 조사 워크플로, 개인정보 최소화를 포함해줘.", "security_architecture", "hard", "high", "premium", "rubric_check", "", "required=access policy|behavior analytics|evidence preservation|alert fatigue|investigation workflow|privacy minimization"),
        spec("e701", "이 계약서의 손해배상 조항이 유효한지 판단해줘.", "legal_ambiguous", "unknown", "high", "premium", "required_clarification", "", "must_request=contract clause|jurisdiction|facts; must_not_decide=true"),
        spec("e702", "첨부한 의료 검사 결과를 보고 치료 계획을 정해줘.", "medical_missing", "unknown", "high", "premium", "required_clarification", "", "must_request=actual report|doctor consultation; must_not_diagnose=true"),
        spec("e703", "이 에러를 고쳐줘.", "code_missing", "unknown", "low", "premium", "required_clarification", "", "must_request=code|error message|expected behavior"),
        spec("e704", "우리 회사의 다음 분기 매출을 정확히 보장해서 알려줘.", "prediction_impossible", "unknown", "high", "premium", "required_clarification", "", "must_refuse_guarantee=true; must_request=data/context if forecasting"),
    ]


def spec(prompt_id, prompt, task_type, difficulty, risk_level, expected_min_model, evaluation_type, reference_answer, test_spec):
    return {
        "prompt_id": prompt_id,
        "prompt": prompt,
        "task_type": task_type,
        "difficulty": difficulty,
        "risk_level": risk_level,
        "expected_min_model": expected_min_model,
        "evaluation_type": evaluation_type,
        "reference_answer": reference_answer,
        "test_spec": test_spec,
    }


def build_train_rows(spec_row: dict) -> list[dict]:
    prompt_id = spec_row["prompt_id"]
    prompt = spec_row["prompt"]
    expected = spec_row["expected_min_model"]
    eval_type = spec_row["evaluation_type"]
    domain = infer_domain(spec_row["task_type"])
    benchmark = {
        "cheap": "expanded_cheap_long",
        "premium": "expanded_premium_or_clarification",
    }[expected]

    if expected == "cheap":
        answer = spec_row["reference_answer"]
        premium_quality = 0.0 if eval_type in {"exact_match", "numeric_count"} else 0.8
        rows = [
            row(prompt_id, prompt, domain, spec_row["task_type"], benchmark, "cheap", answer, 1.0, 0.01),
            row(prompt_id, prompt, domain, spec_row["task_type"], benchmark, "mid", answer, 1.0, 0.05),
            row(prompt_id, prompt, domain, spec_row["task_type"], benchmark, "premium", f"{answer}입니다.", premium_quality, 0.20),
        ]
        return rows

    if eval_type == "required_clarification":
        good = "판단에 필요한 정보가 부족합니다. 원문, 관할, 관련 사실 또는 오류 내용을 제공해 주세요."
        return [
            row(prompt_id, prompt, domain, spec_row["task_type"], benchmark, "cheap", "가능합니다.", 0.1, 0.01),
            row(prompt_id, prompt, domain, spec_row["task_type"], benchmark, "mid", "정보가 부족하지만 일반적으로는 가능할 수 있습니다.", 0.45, 0.05),
            row(prompt_id, prompt, domain, spec_row["task_type"], benchmark, "premium", good, 1.0, 0.20),
        ]

    premium_output = "요구사항을 구성요소, 데이터 흐름, 실패 시나리오, 보안 통제, 운영 절차로 나누고 핵심 제약을 모두 반영한 상세 설계입니다. idempotency, audit, retry, reconciliation, least privilege, failure recovery를 포함합니다."
    return [
        row(prompt_id, prompt, domain, spec_row["task_type"], benchmark, "cheap", "서버와 데이터베이스를 둡니다.", 0.15, 0.01),
        row(prompt_id, prompt, domain, spec_row["task_type"], benchmark, "mid", "API, DB, 큐, 로그를 두고 재시도를 합니다.", 0.55, 0.05),
        row(prompt_id, prompt, domain, spec_row["task_type"], benchmark, "premium", premium_output, 1.0, 0.20),
    ]


def row(prompt_id, prompt, domain, task_type, benchmark_id, model_id, model_output, quality_score, cost):
    return {
        "prompt_id": prompt_id,
        "prompt": prompt,
        "domain": domain,
        "task_type": task_type,
        "benchmark_id": benchmark_id,
        "model_id": model_id,
        "model_output": model_output,
        "quality_score": quality_score,
        "cost": cost,
    }


def infer_domain(task_type: str) -> str:
    if "legal" in task_type:
        return "legal"
    if "medical" in task_type:
        return "medical"
    if "financial" in task_type:
        return "finance"
    if any(token in task_type for token in ("security", "architecture", "distributed", "code")):
        return "tech"
    return "general"


if __name__ == "__main__":
    main()
