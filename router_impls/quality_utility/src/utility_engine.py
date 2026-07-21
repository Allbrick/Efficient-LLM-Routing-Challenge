from __future__ import annotations

from typing import List, Optional

import numpy as np

from .data_models import CostConfig, LambdaParams


class CostNormalizer:
    """비용을 [0, 1] 범위로 정규화한다."""

    def __init__(self, cost_config: CostConfig):
        self.cost_config = cost_config

    def normalize(
        self,
        model_ids: List[str],
        raw_costs: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """모델별 비용을 [0, 1]로 정규화한다.

        Args:
            model_ids: 후보 모델 ID 리스트
            raw_costs: 프롬프트별 가변 비용 (None이면 고정 비용 사용)

        Returns:
            (N,) 정규화된 비용
        """
        if raw_costs is not None:
            costs = raw_costs
        else:
            costs = np.array(
                [self.cost_config.cost_map[mid] for mid in model_ids],
                dtype=np.float64,
            )

        c_range = self.cost_config.c_max - self.cost_config.c_min
        if c_range < 1e-12:
            return np.zeros(len(model_ids), dtype=np.float64)
        return (costs - self.cost_config.c_min) / c_range


class UtilityEngine:
    """Unified Utility 기반 최적 모델 선택 엔진.

    U(m) = Q_calibrated(m) - lambda(tier) * C_norm(m)
    selected = argmax_m U(m)
    """

    def __init__(
        self,
        lambda_params: LambdaParams,
        cost_normalizer: CostNormalizer,
    ):
        self.lambda_params = lambda_params
        self.cost_normalizer = cost_normalizer

    def select(
        self,
        q_calibrated: np.ndarray,
        model_ids: List[str],
        tier: str,
        raw_costs: Optional[np.ndarray] = None,
    ) -> str:
        """최적 모델을 선택한다.

        Args:
            q_calibrated: (N,) 보정된 품질 예측
            model_ids: 후보 모델 ID 리스트
            tier: "fast", "balanced", "premium"
            raw_costs: 프롬프트별 가변 비용 (None이면 고정 비용)

        Returns:
            선택된 model_id
        """
        lam = self.lambda_params.get(tier)
        c_norm = self.cost_normalizer.normalize(model_ids, raw_costs)

        utilities = q_calibrated - lam * c_norm

        # Tie-break: utility가 동일하면 가장 저렴한 모델 선택
        max_util = np.max(utilities)
        tied_mask = np.abs(utilities - max_util) < 1e-8

        if np.sum(tied_mask) > 1:
            tied_costs = c_norm[tied_mask]
            tied_indices = np.where(tied_mask)[0]
            cheapest_among_tied = tied_indices[np.argmin(tied_costs)]
            return model_ids[cheapest_among_tied]

        return model_ids[int(np.argmax(utilities))]

    def compute_utilities(
        self,
        q_calibrated: np.ndarray,
        model_ids: List[str],
        tier: str,
        raw_costs: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """utility 값 자체를 반환 (디버깅/분석용)."""
        lam = self.lambda_params.get(tier)
        c_norm = self.cost_normalizer.normalize(model_ids, raw_costs)
        return q_calibrated - lam * c_norm
