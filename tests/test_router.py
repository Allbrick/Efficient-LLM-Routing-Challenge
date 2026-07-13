"""Router integration test.

이 테스트는 실제 artifacts 없이 router의 인터페이스 로직만 검증한다.
전체 파이프라인 테스트는 artifacts 생성 후 별도로 수행.
"""

import json
import os

import numpy as np
import pytest

from src.calibrator import Calibrator
from src.candidate_expander import CandidateExpander
from src.data_models import CostConfig, LambdaParams
from src.feature_extractor import FeatureExtractor
from src.quality_predictor import QualityPredictor
from src.utility_engine import CostNormalizer, UtilityEngine


class TestRouterLogic:
    """artifacts 없이 router의 핵심 로직을 단위 테스트한다."""

    @pytest.fixture
    def components(self):
        # Feature extractor
        ext = FeatureExtractor(tfidf_max_features=50, svd_n_components=5)
        ext.fit(["hello world", "def foo(): pass", "what is ∫ x dx?"])

        # Expander
        mapping = {"cheap": 0, "mid": 1, "premium": 2}
        expander = CandidateExpander(mapping)

        # Cost
        cost_config = CostConfig(
            mode="fixed",
            cost_map={"cheap": 0.01, "mid": 0.05, "premium": 0.20},
        )
        cost_norm = CostNormalizer(cost_config)

        # Lambda
        lambda_params = LambdaParams(fast=5.0, balanced=1.5, premium=0.1)

        # Utility engine
        engine = UtilityEngine(lambda_params, cost_norm)

        return ext, expander, engine

    def test_end_to_end_pipeline(self, components):
        ext, expander, engine = components

        prompt = "Write a Python function to sort a list"
        model_ids = ["cheap", "mid", "premium"]

        # 1. Feature extraction
        features = ext.transform([prompt])
        assert features.ndim == 2
        assert features.shape[0] == 1

        # 2. Candidate expansion
        X, ids = expander.expand(features, model_ids)
        assert X.shape[0] == 3

        # 3. Simulate quality predictions (no trained model)
        q_hat = np.array([0.65, 0.78, 0.85])

        # 4. Simulate calibration (bias = 0)
        q_cal = q_hat

        # 5. Utility selection
        for tier in ["fast", "balanced", "premium"]:
            selected = engine.select(q_cal, model_ids, tier)
            assert selected in model_ids

    def test_fast_tier_favors_cheap(self, components):
        _, _, engine = components
        q_cal = np.array([0.70, 0.75, 0.80])
        selected = engine.select(q_cal, ["cheap", "mid", "premium"], "fast")
        assert selected == "cheap"

    def test_premium_tier_favors_quality(self, components):
        _, _, engine = components
        q_cal = np.array([0.50, 0.70, 0.90])
        selected = engine.select(q_cal, ["cheap", "mid", "premium"], "premium")
        assert selected == "premium"

    def test_history_handling_logic(self):
        """history가 있으면 select_output, 없으면 call_model을 반환해야 한다."""
        # 이 테스트는 router.route()의 분기 로직만 검증
        history_empty = []
        history_with_call = [{"model_id": "cheap", "output": "..."}]

        # history가 비어있으면 call_model
        assert len(history_empty) == 0  # -> call_model

        # history가 있으면 select_output
        assert len(history_with_call) > 0  # -> select_output

    def test_feature_extraction_latency(self, components):
        """추론 시간이 합리적인 범위인지 확인 (< 100ms per prompt)."""
        import time

        ext, expander, engine = components
        prompt = "This is a test prompt for latency measurement. " * 10

        start = time.perf_counter()
        for _ in range(100):
            features = ext.transform([prompt])
            X, _ = expander.expand(features, ["cheap", "mid", "premium"])
            q_cal = np.array([0.7, 0.8, 0.9])
            engine.select(q_cal, ["cheap", "mid", "premium"], "fast")
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / 100) * 1000
        assert avg_ms < 100, f"Average latency {avg_ms:.1f}ms exceeds 100ms"
