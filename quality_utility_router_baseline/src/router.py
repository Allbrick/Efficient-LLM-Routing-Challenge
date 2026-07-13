from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

import numpy as np

from .feature_extractor import FeatureExtractor
from .candidate_expander import CandidateExpander
from .quality_predictor import QualityPredictor
from .calibrator import Calibrator
from .utility_engine import CostNormalizer, UtilityEngine
from .data_models import CostConfig, LambdaParams
from .prompt_policy import apply_prompt_prior


class PromptTerrainRouterV2:
    """대회 시뮬레이터에 제출할 라우터 클래스.

    오프라인에서 학습된 artifacts를 로드하여 추론한다.
    """

    def __init__(self, artifacts_dir: str = "artifacts"):
        self.feature_extractor = FeatureExtractor.load(
            os.path.join(artifacts_dir, "feature_pipeline.pkl")
        )

        model_id_mapping_path = os.path.join(artifacts_dir, "model_id_mapping.json")
        with open(model_id_mapping_path) as f:
            model_id_mapping = json.load(f)
        self.expander = CandidateExpander(model_id_mapping)

        self.predictor = QualityPredictor.load(
            os.path.join(artifacts_dir, "lgbm_model.txt")
        )

        self.calibrator = Calibrator.load(
            os.path.join(artifacts_dir, "calibration_params.json")
        )

        lambda_params = LambdaParams.load(
            os.path.join(artifacts_dir, "lambda_params.json")
        )
        cost_config = CostConfig.load(
            os.path.join(artifacts_dir, "cost_normalization.json")
        )
        self.utility_engine = UtilityEngine(
            lambda_params=lambda_params,
            cost_normalizer=CostNormalizer(cost_config),
        )

    def route(
        self,
        prompt: str,
        budget_tier: str,
        history: List[Dict],
        candidate_models: List[Dict],
    ) -> Dict:
        """시뮬레이터 인터페이스에 맞는 라우팅 함수.

        Args:
            prompt: 사용자 입력 프롬프트
            budget_tier: "fast" | "balanced" | "premium"
            history: 이전 호출 이력
            candidate_models: 후보 모델 메타데이터 리스트

        Returns:
            {"action": "call_model", "model_id": "..."}
            또는
            {"action": "select_output", "model_id": "..."}
        """
        # 이미 호출된 모델이 있는 경우: 기존 결과 중 최적 선택
        if history:
            called_ids = [h["model_id"] for h in history]
            selected = self._select_best(prompt, called_ids, budget_tier)
            return {"action": "select_output", "model_id": selected}

        # 첫 호출: 최적 모델 1개 선택하여 호출
        model_ids = [m["model_id"] for m in candidate_models]
        selected = self._select_best(prompt, model_ids, budget_tier)
        return {"action": "call_model", "model_id": selected}

    def _select_best(
        self,
        prompt: str,
        model_ids: List[str],
        tier: str,
    ) -> str:
        """주어진 후보 모델 중 최적 모델을 선택한다."""
        # 1. Feature extraction (1회)
        prompt_features = self.feature_extractor.transform([prompt])

        # 2. Candidate expansion
        X, ids = self.expander.expand(prompt_features, model_ids)

        # 3. Quality prediction (batch)
        raw_q = self.predictor.predict(X)

        # 4. Calibration
        model_id_encoded = np.array(
            [self.expander.model_id_mapping[mid] for mid in model_ids],
            dtype=np.int32,
        )
        q_cal = self.calibrator.transform(raw_q, model_id_encoded)
        q_policy = apply_prompt_prior(q_cal, model_ids, prompt, tier)

        # 5. Utility-based selection
        selected = self.utility_engine.select(q_policy, model_ids, tier)
        return selected
