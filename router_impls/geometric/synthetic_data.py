from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np
import pandas as pd

from router_impls.geometric.features import MODEL_ORDER, MODEL_RANK


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


def smote_augment_features(
    prompt_features: dict[str, np.ndarray],
    labels: pd.DataFrame,
    prompt_texts: dict[str, str],
    target_ratio: float = 0.80,
    k_neighbors: int = 3,
    random_state: int = 42,
) -> tuple[dict[str, np.ndarray], pd.DataFrame, dict[str, str]]:
    """Feature-space SMOTE augmentation for minority expected_min_model classes.

    Generates synthetic feature vectors by interpolating between nearest
    neighbors within each minority class.  Only affects pass_model and
    risk_model exemplars -- envelopes are fitted on the original data.
    """
    prompt_labels = labels.drop_duplicates("prompt_id")[["prompt_id", "expected_min_model"]]
    class_counts = Counter(prompt_labels["expected_min_model"])
    majority_count = max(class_counts.values())
    target_count = int(majority_count * target_ratio)

    rng = np.random.RandomState(random_state)
    new_features: dict[str, np.ndarray] = {}
    new_labels_rows: list[dict[str, Any]] = []
    new_texts: dict[str, str] = {}

    for cls, count in class_counts.items():
        if count >= target_count:
            continue

        cls_prompt_ids = prompt_labels.loc[
            prompt_labels["expected_min_model"] == cls, "prompt_id"
        ].tolist()
        cls_prompt_ids = [pid for pid in cls_prompt_ids if pid in prompt_features]
        if len(cls_prompt_ids) < 2:
            continue

        cls_features = np.array(
            [prompt_features[pid] for pid in cls_prompt_ids], dtype=np.float64
        )
        n_synthetic = target_count - count
        k = min(k_neighbors, len(cls_prompt_ids) - 1)

        for i in range(n_synthetic):
            idx = rng.randint(0, len(cls_prompt_ids))
            source = cls_features[idx]

            distances = np.linalg.norm(cls_features - source, axis=1)
            neighbor_indices = np.argsort(distances)[1 : k + 1]
            neighbor_idx = neighbor_indices[rng.randint(0, len(neighbor_indices))]
            neighbor = cls_features[neighbor_idx]

            alpha = rng.random()
            synthetic = source + alpha * (neighbor - source)

            syn_id = f"smote_{cls}_{i:03d}"
            new_features[syn_id] = synthetic
            new_texts[syn_id] = prompt_texts.get(cls_prompt_ids[idx], "")

            for model_id in MODEL_ORDER:
                if cls == "abstain":
                    success = False
                elif model_id in MODEL_RANK and cls in MODEL_RANK:
                    success = MODEL_RANK[model_id] >= MODEL_RANK[cls]
                else:
                    success = False

                new_labels_rows.append(
                    {
                        "prompt_id": syn_id,
                        "model_id": model_id,
                        "success": success,
                        "success_score": 1.0 if success else 0.0,
                        "success_reason": "smote_synthetic",
                        "expected_min_model": cls,
                    }
                )

    merged_features = {**prompt_features, **new_features}
    merged_texts = {**prompt_texts, **new_texts}
    if new_labels_rows:
        merged_labels = pd.concat(
            [labels, pd.DataFrame(new_labels_rows)], ignore_index=True
        )
    else:
        merged_labels = labels

    return merged_features, merged_labels, merged_texts

