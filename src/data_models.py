from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional


@dataclass
class LambdaParams:
    """티어별 비용 민감도 파라미터.

    단조 조건: fast >= balanced >= premium >= 0
    """

    fast: float
    balanced: float
    premium: float

    def __post_init__(self):
        if not (self.fast >= self.balanced >= self.premium >= 0):
            raise ValueError(
                f"단조 조건 위반: fast({self.fast}) >= balanced({self.balanced}) "
                f">= premium({self.premium}) >= 0"
            )

    def get(self, tier: str) -> float:
        tier_lower = tier.lower()
        if tier_lower == "fast":
            return self.fast
        elif tier_lower == "balanced":
            return self.balanced
        elif tier_lower == "premium":
            return self.premium
        else:
            raise ValueError(f"Unknown tier: {tier}")

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: str) -> LambdaParams:
        with open(path) as f:
            return cls(**json.load(f))


@dataclass
class CostConfig:
    """비용 정규화 설정.

    mode:
        "fixed" - 모델별 고정 비용 (min-max 정규화)
        "variable" - 프롬프트별 가변 비용 (input_cost + avg_output_cost)
    """

    mode: str  # "fixed" or "variable"
    cost_map: Dict[str, float]  # model_id -> raw cost
    c_min: Optional[float] = None
    c_max: Optional[float] = None

    def __post_init__(self):
        costs = list(self.cost_map.values())
        if self.c_min is None:
            self.c_min = min(costs)
        if self.c_max is None:
            self.c_max = max(costs)

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(
                {"mode": self.mode, "cost_map": self.cost_map,
                 "c_min": self.c_min, "c_max": self.c_max},
                f, indent=2,
            )

    @classmethod
    def load(cls, path: str) -> CostConfig:
        with open(path) as f:
            return cls(**json.load(f))


@dataclass
class CalibrationParams:
    """모델별 calibration 파라미터."""

    method: str  # "bias" or "linear"
    params: Dict[str, Dict[str, float]]
    # bias:   {"cheap": {"bias": 0.03}, ...}
    # linear: {"cheap": {"slope": 1.02, "intercept": -0.01}, ...}

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump({"method": self.method, "params": self.params}, f, indent=2)

    @classmethod
    def load(cls, path: str) -> CalibrationParams:
        with open(path) as f:
            data = json.load(f)
            return cls(method=data["method"], params=data["params"])
