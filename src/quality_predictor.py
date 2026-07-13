from __future__ import annotations

from typing import Dict, List, Optional

import lightgbm as lgb
import numpy as np


DEFAULT_LGB_PARAMS = {
    "objective": "regression",
    "metric": "mae",
    "num_leaves": 31,
    "learning_rate": 0.05,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "verbose": -1,
    "seed": 42,
}


class QualityPredictor:
    """LightGBM 기반 품질 점수 예측기.

    단일 모델로 모든 (prompt, model) 쌍의 품질을 예측한다.
    model_id는 categorical feature로 처리.
    """

    def __init__(self, lgbm_params: Optional[Dict] = None):
        self.lgbm_params = lgbm_params or DEFAULT_LGB_PARAMS.copy()
        self._model: Optional[lgb.Booster] = None
        self._best_iteration: Optional[int] = None

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        categorical_feature: List[int],
        num_boost_round: int = 2000,
        early_stopping_rounds: int = 50,
    ) -> Dict[str, float]:
        """early stopping 기반 학습.

        Returns:
            {"best_iteration": int, "best_val_mae": float}
        """
        train_data = lgb.Dataset(
            X_train, label=y_train,
            categorical_feature=categorical_feature,
            free_raw_data=False,
        )
        val_data = lgb.Dataset(
            X_val, label=y_val,
            categorical_feature=categorical_feature,
            reference=train_data,
            free_raw_data=False,
        )

        callbacks = [
            lgb.early_stopping(stopping_rounds=early_stopping_rounds),
            lgb.log_evaluation(period=100),
        ]

        self._model = lgb.train(
            self.lgbm_params,
            train_data,
            num_boost_round=num_boost_round,
            valid_sets=[val_data],
            valid_names=["val"],
            callbacks=callbacks,
        )

        self._best_iteration = self._model.best_iteration

        val_pred = self._model.predict(X_val)
        best_val_mae = float(np.mean(np.abs(y_val - val_pred)))

        return {
            "best_iteration": self._best_iteration,
            "best_val_mae": best_val_mae,
        }

    def train_final(
        self,
        X: np.ndarray,
        y: np.ndarray,
        categorical_feature: List[int],
        num_boost_round: int,
    ) -> None:
        """최종 모델 빌드. val 없이 지정된 라운드로 학습."""
        train_data = lgb.Dataset(
            X, label=y,
            categorical_feature=categorical_feature,
            free_raw_data=False,
        )
        self._model = lgb.train(
            self.lgbm_params,
            train_data,
            num_boost_round=num_boost_round,
        )
        self._best_iteration = num_boost_round

    def predict(self, X: np.ndarray) -> np.ndarray:
        """batch predict. shape: (N, D+1) -> (N,)"""
        if self._model is None:
            raise RuntimeError("모델이 학습되지 않았습니다.")
        return self._model.predict(X)

    @property
    def feature_importance(self) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("모델이 학습되지 않았습니다.")
        return self._model.feature_importance(importance_type="gain")

    def save(self, path: str) -> None:
        if self._model is None:
            raise RuntimeError("모델이 학습되지 않았습니다.")
        self._model.save_model(path, num_iteration=self._best_iteration)

    @classmethod
    def load(cls, path: str) -> QualityPredictor:
        obj = cls()
        obj._model = lgb.Booster(model_file=path)
        return obj
