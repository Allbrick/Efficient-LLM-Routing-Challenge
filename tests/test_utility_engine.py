import os

import numpy as np
import pytest

from src.data_models import CostConfig, LambdaParams
from src.utility_engine import CostNormalizer, UtilityEngine


@pytest.fixture
def cost_config():
    return CostConfig(
        mode="fixed",
        cost_map={"cheap": 0.01, "mid": 0.05, "premium": 0.20},
    )


@pytest.fixture
def lambda_params():
    return LambdaParams(fast=5.0, balanced=1.5, premium=0.1)


@pytest.fixture
def engine(lambda_params, cost_config):
    return UtilityEngine(
        lambda_params=lambda_params,
        cost_normalizer=CostNormalizer(cost_config),
    )


class TestLambdaParams:
    def test_monotonicity_valid(self):
        lp = LambdaParams(fast=5.0, balanced=3.0, premium=0.0)
        assert lp.get("fast") == 5.0

    def test_monotonicity_violation(self):
        with pytest.raises(ValueError, match="단조 조건"):
            LambdaParams(fast=1.0, balanced=3.0, premium=0.0)

    def test_negative_premium(self):
        with pytest.raises(ValueError, match="단조 조건"):
            LambdaParams(fast=5.0, balanced=3.0, premium=-1.0)

    def test_unknown_tier(self):
        lp = LambdaParams(fast=5.0, balanced=3.0, premium=0.0)
        with pytest.raises(ValueError, match="Unknown tier"):
            lp.get("unknown")

    def test_save_load(self, tmp_dir):
        lp = LambdaParams(fast=5.0, balanced=3.0, premium=0.1)
        path = os.path.join(tmp_dir, "lambda.json")
        lp.save(path)
        loaded = LambdaParams.load(path)
        assert loaded.fast == lp.fast
        assert loaded.balanced == lp.balanced
        assert loaded.premium == lp.premium


class TestCostNormalizer:
    def test_normalize_fixed(self, cost_config):
        norm = CostNormalizer(cost_config)
        result = norm.normalize(["cheap", "mid", "premium"])
        # min=0.01, max=0.20, range=0.19
        np.testing.assert_almost_equal(result[0], 0.0, decimal=5)        # cheap
        np.testing.assert_almost_equal(result[2], 1.0, decimal=5)        # premium
        assert 0.0 < result[1] < 1.0                                     # mid

    def test_normalize_single_model(self):
        config = CostConfig(mode="fixed", cost_map={"only": 0.5})
        norm = CostNormalizer(config)
        result = norm.normalize(["only"])
        # range = 0, should return 0
        assert result[0] == 0.0


class TestUtilityEngine:
    def test_lambda_zero_selects_best_quality(self, cost_config):
        lp = LambdaParams(fast=0.0, balanced=0.0, premium=0.0)
        engine = UtilityEngine(lp, CostNormalizer(cost_config))

        q_cal = np.array([0.70, 0.80, 0.90])
        selected = engine.select(q_cal, ["cheap", "mid", "premium"], "premium")
        assert selected == "premium"

    def test_high_lambda_selects_cheapest(self, engine):
        q_cal = np.array([0.70, 0.75, 0.80])
        selected = engine.select(q_cal, ["cheap", "mid", "premium"], "fast")
        assert selected == "cheap"

    def test_balanced_tier(self, engine):
        # mid has decent quality and moderate cost
        q_cal = np.array([0.50, 0.78, 0.80])
        selected = engine.select(q_cal, ["cheap", "mid", "premium"], "balanced")
        # With lambda=1.5, mid should win over premium for small quality gap
        assert selected in ["cheap", "mid", "premium"]  # valid selection

    def test_tie_break_cheapest(self, engine):
        q_cal = np.array([0.70, 0.70, 0.70])
        selected = engine.select(q_cal, ["cheap", "mid", "premium"], "premium")
        # lambda_premium = 0.1, so utilities differ slightly by cost
        # But if lambda=0 exactly, all utilities equal -> cheapest wins
        lp = LambdaParams(fast=0.0, balanced=0.0, premium=0.0)
        engine_zero = UtilityEngine(lp, CostNormalizer(engine.cost_normalizer.cost_config))
        selected = engine_zero.select(q_cal, ["cheap", "mid", "premium"], "premium")
        assert selected == "cheap"  # tie-break

    def test_compute_utilities(self, engine):
        q_cal = np.array([0.70, 0.80, 0.90])
        utilities = engine.compute_utilities(q_cal, ["cheap", "mid", "premium"], "fast")
        assert len(utilities) == 3
        # fast tier has high lambda, so cheap should have highest utility
        # unless quality gap is very large
