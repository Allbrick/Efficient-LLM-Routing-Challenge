from __future__ import annotations

from pathlib import Path

import numpy as np

from router_impls.quality_utility.src.calibrator import Calibrator
from router_impls.quality_utility.src.candidate_expander import CandidateExpander
from router_impls.quality_utility.src.data_models import CostConfig, LambdaParams
from router_impls.quality_utility.src.feature_extractor import FeatureExtractor
from router_impls.quality_utility.src.prompt_policy import apply_prompt_prior, estimate_prompt_complexity
from router_impls.quality_utility.src.quality_predictor import QualityPredictor
from router_impls.quality_utility.src.utility_engine import CostNormalizer, UtilityEngine
from routing_stack.adapters.contract import Candidate, RouteRequest, RouteResult


class QualityUtilityRouterAdapter:
    name = "quality_utility"

    def __init__(self, artifacts_dir: str | Path = "router_impls/quality_utility/artifacts"):
        artifacts = Path(artifacts_dir)
        self.feature_extractor = FeatureExtractor.load(str(artifacts / "feature_pipeline.pkl"))
        self.expander = CandidateExpander.load(str(artifacts / "model_id_mapping.json"))
        self.predictor = QualityPredictor.load(str(artifacts / "lgbm_model.txt"))
        self.calibrator = Calibrator.load(str(artifacts / "calibration_params.json"))
        self.lambda_params = LambdaParams.load(str(artifacts / "lambda_params.json"))
        self.cost_config = CostConfig.load(str(artifacts / "cost_normalization.json"))
        self.utility_engine = UtilityEngine(self.lambda_params, CostNormalizer(self.cost_config))
        self.model_ids = sorted(self.expander.model_id_mapping, key=self.expander.model_id_mapping.get)

    def route(self, request: RouteRequest) -> RouteResult:
        tier = self._resolve_tier(request.prompt, request.tier)
        prompt_features = self.feature_extractor.transform([request.prompt])
        expanded, model_ids = self.expander.expand(prompt_features, self.model_ids)
        raw_quality = self.predictor.predict(expanded)
        encoded = np.array([self.expander.model_id_mapping[mid] for mid in model_ids], dtype=np.int32)
        calibrated_quality = self.calibrator.transform(raw_quality, encoded)
        policy_quality = apply_prompt_prior(calibrated_quality, model_ids, request.prompt, tier)
        policy_quality = self._apply_context_prior(policy_quality, model_ids, request.context_features)
        utilities = self.utility_engine.compute_utilities(policy_quality, model_ids, tier)
        selected = self.utility_engine.select(policy_quality, model_ids, tier)

        candidates = []
        for idx, model_id in enumerate(model_ids):
            candidates.append(
                Candidate(
                    model_id=model_id,
                    score=float(utilities[idx]),
                    cost=float(self.cost_config.cost_map[model_id]),
                    feasible=True,
                    reason="max_utility",
                    metrics={
                        "predicted_quality": round(float(raw_quality[idx]), 6),
                        "calibrated_quality": round(float(calibrated_quality[idx]), 6),
                        "policy_quality": round(float(policy_quality[idx]), 6),
                        "utility": round(float(utilities[idx]), 6),
                    },
                )
            )
        return RouteResult(
            router_name=self.name,
            selected_model_id=selected,
            action_type="call_model",
            selection_reason="max_utility",
            candidates=candidates,
            diagnostics={
                "prompt": request.prompt,
                "requested_tier": request.tier,
                "resolved_tier": tier,
                "prompt_complexity": round(float(estimate_prompt_complexity(request.prompt)), 6),
                "lambda": self.lambda_params.get(tier),
                "input_features": request.input_features,
                "context_features": request.context_features,
            },
        )

    def _resolve_tier(self, prompt: str, tier: str) -> str:
        if tier != "auto":
            return tier
        complexity = estimate_prompt_complexity(prompt)
        if complexity < 0.28:
            return "fast"
        if complexity < 0.62:
            return "balanced"
        return "premium"

    def _apply_context_prior(self, qualities, model_ids, context_features: dict):
        adjusted = np.array(qualities, dtype=np.float64, copy=True)
        if not context_features:
            return adjusted
        for idx, model_id in enumerate(model_ids):
            if context_features.get("missing_context"):
                adjusted[idx] -= 0.35
            if model_id == "cheap" and context_features.get("previous_cheap_failure"):
                adjusted[idx] -= 0.18
            if model_id == "mid" and context_features.get("previous_cheap_failure"):
                adjusted[idx] += 0.08
            if context_features.get("references_code") and float(context_features.get("context_token_pressure", 0.0) or 0.0) >= 0.40:
                if model_id == "cheap":
                    adjusted[idx] -= 0.12
                if model_id == "mid":
                    adjusted[idx] += 0.08
            if context_features.get("references_design") and context_features.get("requires_cross_turn_reasoning"):
                if model_id in {"mid", "premium"}:
                    adjusted[idx] += 0.06
        return adjusted


