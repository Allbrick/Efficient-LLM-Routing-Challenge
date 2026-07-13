import os

import numpy as np
import pytest

from src.calibrator import Calibrator


@pytest.fixture
def sample_data():
    """model 0은 +0.1 과대예측, model 1은 -0.05 과소예측."""
    q_hat = np.array([0.80, 0.85, 0.90, 0.60, 0.65, 0.70])
    q_true = np.array([0.70, 0.75, 0.80, 0.65, 0.70, 0.75])
    model_ids = np.array([0, 0, 0, 1, 1, 1])
    prompt_ids = np.array([0, 1, 2, 0, 1, 2])
    return q_hat, q_true, model_ids, prompt_ids


class TestCalibrator:
    def test_bias_correction(self, sample_data):
        q_hat, q_true, model_ids, _ = sample_data
        cal = Calibrator(method="bias")
        cal.fit(q_hat, q_true, model_ids)

        q_cal = cal.transform(q_hat, model_ids)

        # model 0: bias = mean(q_true - q_hat) = mean([-0.1, -0.1, -0.1]) = -0.1
        np.testing.assert_almost_equal(q_cal[0], 0.70, decimal=5)
        np.testing.assert_almost_equal(q_cal[1], 0.75, decimal=5)

        # model 1: bias = mean([0.05, 0.05, 0.05]) = 0.05
        np.testing.assert_almost_equal(q_cal[3], 0.65, decimal=5)

    def test_linear_correction(self, sample_data):
        q_hat, q_true, model_ids, _ = sample_data
        cal = Calibrator(method="linear")
        cal.fit(q_hat, q_true, model_ids)

        q_cal = cal.transform(q_hat, model_ids)
        # linear fit should reduce error
        mae_before = np.mean(np.abs(q_true - q_hat))
        mae_after = np.mean(np.abs(q_true - q_cal))
        assert mae_after <= mae_before + 1e-5

    def test_mean_residual_near_zero_after_bias(self, sample_data):
        q_hat, q_true, model_ids, _ = sample_data
        cal = Calibrator(method="bias")
        cal.fit(q_hat, q_true, model_ids)

        q_cal = cal.transform(q_hat, model_ids)
        for mid in [0, 1]:
            mask = model_ids == mid
            residual = np.mean(q_true[mask] - q_cal[mask])
            np.testing.assert_almost_equal(residual, 0.0, decimal=5)

    def test_evaluate_metrics(self, sample_data):
        q_hat, q_true, model_ids, prompt_ids = sample_data
        cal = Calibrator(method="bias")
        cal.fit(q_hat, q_true, model_ids)

        metrics = cal.evaluate(q_hat, q_true, model_ids, prompt_ids)
        assert "overall_mae" in metrics
        assert "pairwise_ranking_accuracy" in metrics
        assert "best_model_selection_accuracy" in metrics
        assert 0.0 <= metrics["pairwise_ranking_accuracy"] <= 1.0
        assert 0.0 <= metrics["best_model_selection_accuracy"] <= 1.0

    def test_transform_before_fit_raises(self):
        cal = Calibrator()
        with pytest.raises(RuntimeError, match="fit"):
            cal.transform(np.array([0.5]), np.array([0]))

    def test_invalid_method(self):
        with pytest.raises(ValueError, match="bias"):
            Calibrator(method="invalid")

    def test_save_load(self, sample_data, tmp_dir):
        q_hat, q_true, model_ids, _ = sample_data
        cal = Calibrator(method="bias")
        cal.fit(q_hat, q_true, model_ids)

        path = os.path.join(tmp_dir, "cal.json")
        cal.save(path)
        loaded = Calibrator.load(path)

        q_cal_original = cal.transform(q_hat, model_ids)
        q_cal_loaded = loaded.transform(q_hat, model_ids)
        np.testing.assert_array_almost_equal(q_cal_original, q_cal_loaded)
