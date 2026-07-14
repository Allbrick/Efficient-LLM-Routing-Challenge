from __future__ import annotations

import pandas as pd


def build_numeric_count_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build deterministic numeric-count examples as training data, not router rules."""
    examples = [
        (
            "g_count_001",
            '다음 문단에서 "사과"라는 단어가 몇 번 등장하는지만 알려주세요.\n\n'
            + ("사과 바나나 포도 사과 귤 " * 40),
            "80",
        ),
        (
            "g_count_002",
            "아래 텍스트에서 error가 등장하는 횟수만 숫자로 답하세요.\n\n"
            + ("ok error ok warning error " * 30),
            "60",
        ),
        (
            "g_count_003",
            "다음 목록에서 A로 시작하는 항목 개수만 답해줘: Apple, Atom, Banana, Azure, Cat",
            "3",
        ),
        (
            "g_count_004",
            '문자열 "ababababa"에서 "aba"가 몇 번 나오는지 숫자만 답해.',
            "3",
        ),
        (
            "g_count_005",
            "Count only how many times red appears: red blue red green red yellow.",
            "3",
        ),
        (
            "g_count_006",
            "다음 문장에서 쉼표로 구분된 값의 개수만 알려줘: a,b,c,d,e,f",
            "6",
        ),
        (
            "g_count_007",
            '다음 문단에서 "사과"라는 단어가 몇 번 등장하는지만 알려주세요.\n\n'
            + ("사과 바나나 포도 사과 귤사과 바나나 포도 사과 귤" * 60),
            "240",
        ),
        (
            "g_count_008",
            "아래 긴 로그에서 WARN이 몇 번 나오는지만 숫자로 답해줘.\n\n"
            + ("INFO INFO WARN DEBUG INFO WARN " * 80),
            "160",
        ),
        (
            "g_count_009",
            "아래 문단에서 target 문자열의 등장 횟수만 반환하세요.\n\n"
            + ("target alpha beta gamma target delta " * 90),
            "180",
        ),
    ]

    train_rows = []
    spec_rows = []
    for prompt_id, prompt, answer in examples:
        spec_rows.append(
            {
                "prompt_id": prompt_id,
                "prompt": prompt,
                "task_type": "numeric_count",
                "difficulty": "trivial",
                "risk_level": "low",
                "expected_min_model": "cheap",
                "evaluation_type": "numeric_count",
                "reference_answer": answer,
                "test_spec": "numeric count exact answer",
            }
        )
        for model_id, output, quality, cost in [
            ("cheap", answer, 1.0, 0.01),
            ("mid", answer, 1.0, 0.05),
            ("premium", f"{answer}입니다.", 0.0, 0.20),
        ]:
            train_rows.append(
                {
                    "prompt_id": prompt_id,
                    "prompt": prompt,
                    "domain": "general",
                    "task_type": "numeric_count",
                    "benchmark_id": "synthetic_numeric_count",
                    "model_id": model_id,
                    "model_output": output,
                    "quality_score": quality,
                    "cost": cost,
                }
            )

    return pd.DataFrame(train_rows), pd.DataFrame(spec_rows)
