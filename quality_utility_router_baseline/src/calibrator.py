from __future__ import annotations

from typing import Dict

import numpy as np

from .data_models import CalibrationParams


class Calibrator:
    """model-wise bias correction으로 Q_hat을 보정한다.

    목적: 모델별 체계적 편향 제거.
    """

    def __init__(self, method: str = "bias"):
        """
        Args:
            method: "bias" (MVP) 또는 "linear" (데이터 충분 시)
        """
        if method not in ("bias", "linear"):
            raise ValueError(f"method는 'bias' 또는 'linear'이어야 합니다: {method}")
        self.method = method
        self._params: Dict[int, Dict[str, float]] = {}
        self._is_fitted = False

    def fit(
        self,
        q_hat: np.ndarray,
        q_true: np.ndarray,
        model_ids: np.ndarray,
    ) -> Calibrator:
        """OOF predictions으로 calibration 파라미터를 학습한다.

        Args:
            q_hat: (N,) raw predictions
            q_true: (N,) actual quality scores
            model_ids: (N,) integer-encoded model ids
        """
        unique_ids = np.unique(model_ids)

        for mid in unique_ids:
            mask = model_ids == mid
            q_h = q_hat[mask]
            q_t = q_true[mask]
            residuals = q_t - q_h

            if self.method == "bias":
                self._params[int(mid)] = {"bias": float(np.mean(residuals))}
            elif self.method == "linear":
                if len(q_h) < 2 or np.std(q_h) < 1e-8:
                    self._params[int(mid)] = {"slope": 1.0, "intercept": float(np.mean(residuals))}
                else:
                    slope, intercept = np.polyfit(q_h, q_t, 1)
                    self._params[int(mid)] = {"slope": float(slope), "intercept": float(intercept)}

        self._is_fitted = True
        return self

    def transform(
        self,
        q_hat: np.ndarray,
        model_ids: np.ndarray,
    ) -> np.ndarray:
        """raw Q_hat을 보정한다.

        Args:
            q_hat: (N,) raw predictions
            model_ids: (N,) integer-encoded model ids

        Returns:
            q_calibrated: (N,)
        """
        if not self._is_fitted:
            raise RuntimeError("Calibrator.fit()을 먼저 호출하세요.")

        q_cal = np.copy(q_hat)

        for mid, params in self._params.items():
            mask = model_ids == mid
            if not np.any(mask):
                continue
            if self.method == "bias":
                q_cal[mask] += params["bias"]
            elif self.method == "linear":
                q_cal[mask] = params["slope"] * q_hat[mask] + params["intercept"]

        return q_cal

    def evaluate(
        self,
        q_hat: np.ndarray,
        q_true: np.ndarray,
        model_ids: np.ndarray,
        prompt_ids: np.ndarray,
    ) -> Dict[str, float]:
        """Calibration 품질 평가 지표를 계산한다.

        Returns:
            {
                "overall_mae": ...,
                "pairwise_ranking_accuracy": ...,
                "best_model_selection_accuracy": ...,
            }
        """
        q_cal = self.transform(q_hat, model_ids)

        # Overall MAE
        overall_mae = float(np.mean(np.abs(q_true - q_cal)))

        # Pairwise ranking accuracy & best-model selection accuracy
        unique_prompts = np.unique(prompt_ids)
        pairwise_correct = 0
        pairwise_total = 0
        best_correct = 0

        for pid in unique_prompts:
            mask = prompt_ids == pid
            cal_vals = q_cal[mask]
            true_vals = q_true[mask]

            # Best-model selection
            if np.argmax(cal_vals) == np.argmax(true_vals):
                best_correct += 1

            # Pairwise ranking
            n = len(cal_vals)
            for i in range(n):
                for j in range(i + 1, n):
                    pairwise_total += 1
                    cal_order = cal_vals[i] > cal_vals[j]
                    true_order = true_vals[i] > true_vals[j]
                    if cal_order == true_order or true_vals[i] == true_vals[j]:
                        pairwise_correct += 1

        pairwise_acc = pairwise_correct / max(pairwise_total, 1)
        best_acc = best_correct / max(len(unique_prompts), 1)

        return {
            "overall_mae": overall_mae,
            "pairwise_ranking_accuracy": float(pairwise_acc),
            "best_model_selection_accuracy": float(best_acc),
        }

    def to_params(self) -> CalibrationParams:
        str_params = {str(k): v for k, v in self._params.items()}
        return CalibrationParams(method=self.method, params=str_params)

    def save(self, path: str) -> None:
        self.to_params().save(path)

    @classmethod
    def load(cls, path: str) -> Calibrator:
        cp = CalibrationParams.load(path)
        obj = cls(method=cp.method)
        obj._params = {int(k): v for k, v in cp.params.items()}
        obj._is_fitted = True
        return obj
