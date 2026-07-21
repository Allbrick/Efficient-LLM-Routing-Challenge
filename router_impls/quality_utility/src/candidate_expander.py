from __future__ import annotations

import json
from typing import Dict, List, Tuple

import numpy as np


class CandidateExpander:
    """prompt_features를 후보 모델 수만큼 확장하고 model_id를 결합한다.

    prompt_features: (1, D) -> expanded: (N, D+1)
    N = 후보 모델 수
    마지막 컬럼이 model_id (integer encoded, LightGBM categorical).
    """

    def __init__(self, model_id_mapping: Dict[str, int]):
        """
        Args:
            model_id_mapping: {"cheap": 0, "mid": 1, "premium": 2}
        """
        self.model_id_mapping = model_id_mapping
        self._reverse_mapping = {v: k for k, v in model_id_mapping.items()}

    @property
    def model_id_col_index(self) -> int:
        """확장된 feature matrix에서 model_id 컬럼의 인덱스.

        항상 마지막 컬럼.
        prompt_features 차원은 동적이므로, expand 결과의 shape[-1] - 1.
        """
        return -1  # 항상 마지막

    def expand(
        self,
        prompt_features: np.ndarray,
        candidate_model_ids: List[str],
    ) -> Tuple[np.ndarray, List[str]]:
        """prompt_features를 후보 모델 수만큼 확장한다.

        Args:
            prompt_features: shape (1, D) - 단일 프롬프트의 feature 벡터
            candidate_model_ids: ["cheap", "mid", "premium"] 등

        Returns:
            features: shape (N, D+1) - prompt_features 복제 + model_id 컬럼
            model_ids: 원본 model_id 리스트 (결과 매핑용)
        """
        n = len(candidate_model_ids)
        repeated = np.repeat(prompt_features, n, axis=0)  # (N, D)

        model_col = np.array(
            [self.model_id_mapping[mid] for mid in candidate_model_ids],
            dtype=np.float32,
        ).reshape(-1, 1)

        features = np.hstack([repeated, model_col])  # (N, D+1)
        return features, candidate_model_ids

    def expand_batch(
        self,
        prompt_features_batch: np.ndarray,
        candidate_model_ids: List[str],
    ) -> Tuple[np.ndarray, np.ndarray]:
        """여러 프롬프트를 한번에 확장한다. 학습 데이터 생성용.

        Args:
            prompt_features_batch: shape (P, D) - P개 프롬프트
            candidate_model_ids: 모든 프롬프트에 동일하게 적용할 모델 리스트

        Returns:
            features: shape (P*N, D+1)
            prompt_indices: shape (P*N,) - 원본 프롬프트 인덱스
        """
        p, d = prompt_features_batch.shape
        n = len(candidate_model_ids)

        repeated = np.repeat(prompt_features_batch, n, axis=0)  # (P*N, D)

        model_ids_encoded = np.array(
            [self.model_id_mapping[mid] for mid in candidate_model_ids],
            dtype=np.float32,
        )
        model_col = np.tile(model_ids_encoded, p).reshape(-1, 1)  # (P*N, 1)

        features = np.hstack([repeated, model_col])  # (P*N, D+1)
        prompt_indices = np.repeat(np.arange(p), n)   # (P*N,)
        return features, prompt_indices

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.model_id_mapping, f, indent=2)

    @classmethod
    def load(cls, path: str) -> CandidateExpander:
        with open(path) as f:
            return cls(json.load(f))
