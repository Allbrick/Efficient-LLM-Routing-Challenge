from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from router_impls.geometric.envelope import Envelope, fit_envelope
from router_impls.geometric.evaluator import build_training_labels
from router_impls.geometric.features import MODEL_ORDER, EvidenceExtractor
from router_impls.geometric.pass_model import PassProbabilityModel, fit_pass_model
from router_impls.geometric.pareto import best_under_budget, build_pareto_frontier
from router_impls.geometric.risk_model import SufficiencyRiskModel, fit_risk_model
from router_impls.geometric.synthetic_data import build_numeric_count_data
from router_impls.geometric.task_classifier import TaskClassifier


BUDGET_LIMITS = {
    "fast": 0.03,
    "balanced": 0.08,
    "premium": 0.20,
}

DEFAULT_RADIUS_MULTIPLIERS = {
    "fast": {"cheap": 1.10, "mid": 1.10, "premium": 1.10},
    "balanced": {"cheap": 1.00, "mid": 1.00, "premium": 1.00},
    "premium": {"cheap": 0.92, "mid": 0.92, "premium": 0.92},
}

DEFAULT_FALLBACK_COST_WEIGHT = {
    "fast": 0.0,
    "balanced": 0.0,
    "premium": 0.0,
}

DEFAULT_PASS_THRESHOLDS = {
    "fast": 0.74,
    "balanced": 0.82,
    "premium": 0.90,
}

DEFAULT_ABSTAIN_THRESHOLDS = {
    "fast": 0.55,
    "balanced": 0.55,
    "premium": 0.55,
}


@dataclass
class RouteDecision:
    prompt: str
    budget_tier: str
    selected_model_id: str
    selection_reason: str
    evidence: dict
    candidates: list[dict]
    frontier_hint: dict | None


class GeometricRouter:
    def __init__(
        self,
        envelopes: dict[str, Envelope],
        model_costs: dict[str, float],
        frontier: list[dict],
        task_classifier: TaskClassifier | None = None,
        pass_model: PassProbabilityModel | None = None,
        risk_model: SufficiencyRiskModel | None = None,
        radius_multipliers: dict[str, dict[str, float]] | None = None,
        fallback_cost_weight: dict[str, float] | None = None,
        pass_thresholds: dict[str, float] | None = None,
        abstain_thresholds: dict[str, float] | None = None,
        metadata: dict | None = None,
    ):
        self.envelopes = envelopes
        self.model_costs = model_costs
        self.frontier = frontier
        self.task_classifier = task_classifier
        self.pass_model = pass_model
        self.risk_model = risk_model
        self.radius_multipliers = radius_multipliers or {
            tier: values.copy() for tier, values in DEFAULT_RADIUS_MULTIPLIERS.items()
        }
        self.fallback_cost_weight = fallback_cost_weight or DEFAULT_FALLBACK_COST_WEIGHT.copy()
        self.pass_thresholds = pass_thresholds or DEFAULT_PASS_THRESHOLDS.copy()
        self.abstain_thresholds = abstain_thresholds or DEFAULT_ABSTAIN_THRESHOLDS.copy()
        self.metadata = metadata or {}
        self.extractor = EvidenceExtractor()

    @classmethod
    def fit(
        cls,
        train_df: pd.DataFrame,
        specs_df: pd.DataFrame | None = None,
        fallback_threshold: float = 0.85,
        radius_quantile: float = 0.90,
        include_synthetic: bool = True,
    ) -> "GeometricRouter":
        if include_synthetic:
            synthetic_train, synthetic_specs = build_numeric_count_data()
            train_df = pd.concat([train_df, synthetic_train], ignore_index=True)
            if specs_df is None or specs_df.empty:
                specs_df = synthetic_specs
            else:
                specs_df = pd.concat([specs_df, synthetic_specs], ignore_index=True)

        labels = build_training_labels(train_df, specs_df, fallback_threshold=fallback_threshold)
        merged = train_df.merge(labels, on=["prompt_id", "model_id"], how="left")
        spec_map = {}
        if specs_df is not None and not specs_df.empty:
            spec_map = {row.prompt_id: row._asdict() for row in specs_df.itertuples(index=False)}

        extractor = EvidenceExtractor()
        prompt_features = {}
        prompt_texts = {}
        for prompt_id, group in train_df.groupby("prompt_id", sort=False):
            first = group.iloc[0]
            prompt_texts[prompt_id] = str(first["prompt"])
            spec = spec_map.get(prompt_id, {})
            prompt_features[prompt_id] = extractor.transform(
                first["prompt"],
                task_type=str(spec.get("task_type", first.get("task_type", ""))),
                difficulty=str(spec.get("difficulty", "")),
                risk_level=str(spec.get("risk_level", "")),
                evaluation_type=str(spec.get("evaluation_type", "")),
            ).as_vector()

        envelopes = {}
        all_features = np.array(list(prompt_features.values()), dtype=np.float64)
        for model_id in MODEL_ORDER:
            successful_prompt_ids = merged.loc[
                (merged["model_id"] == model_id) & (merged["success"] == True), "prompt_id"
            ].tolist()
            features = np.array([prompt_features[pid] for pid in successful_prompt_ids], dtype=np.float64)
            if len(features) == 0:
                features = all_features
            envelopes[model_id] = fit_envelope(model_id, features, quantile=radius_quantile)

        model_costs = (
            train_df.groupby("model_id")["cost"].mean().astype(float).to_dict()
        )
        frontier = build_pareto_frontier(train_df)
        task_classifier = TaskClassifier.fit(specs_df) if specs_df is not None and not specs_df.empty else None
        pass_model = fit_pass_model(prompt_features, labels)
        risk_model = fit_risk_model(prompt_features, labels, prompt_texts)
        metadata = {
            "fallback_threshold": fallback_threshold,
            "radius_quantile": radius_quantile,
            "include_synthetic": include_synthetic,
            "n_prompts": int(train_df["prompt_id"].nunique()),
            "n_rows": int(len(train_df)),
        }
        return cls(
            envelopes=envelopes,
            model_costs=model_costs,
            frontier=frontier,
            task_classifier=task_classifier,
            pass_model=pass_model,
            risk_model=risk_model,
            metadata=metadata,
        )

    def set_policy(
        self,
        radius_multipliers: dict[str, dict[str, float]] | None = None,
        fallback_cost_weight: dict[str, float] | None = None,
        pass_thresholds: dict[str, float] | None = None,
        abstain_thresholds: dict[str, float] | None = None,
    ) -> None:
        if radius_multipliers is not None:
            self.radius_multipliers = radius_multipliers
        if fallback_cost_weight is not None:
            self.fallback_cost_weight = fallback_cost_weight
        if pass_thresholds is not None:
            self.pass_thresholds = pass_thresholds
        if abstain_thresholds is not None:
            self.abstain_thresholds = abstain_thresholds

    def route(
        self,
        prompt: str,
        budget_tier: str = "balanced",
        task_type: str = "",
        difficulty: str = "",
        risk_level: str = "",
        evaluation_type: str = "",
    ) -> RouteDecision:
        tier = budget_tier.lower()
        if tier not in BUDGET_LIMITS:
            raise ValueError(f"unknown budget_tier: {budget_tier}")

        if self.task_classifier is not None and not evaluation_type:
            inferred = self.task_classifier.predict(prompt)
            task_type = task_type or str(inferred["task_type"])
            difficulty = difficulty or str(inferred["difficulty"])
            risk_level = risk_level or str(inferred["risk_level"])
            evaluation_type = str(inferred["evaluation_type"])

        evidence_obj = self.extractor.transform(prompt, task_type, difficulty, risk_level, evaluation_type)
        x = evidence_obj.as_vector()
        tier_radius = self.radius_multipliers.get(tier, DEFAULT_RADIUS_MULTIPLIERS[tier])
        pass_probabilities = self.pass_model.predict_all(x) if self.pass_model is not None else {}
        sufficiency_probabilities = self.risk_model.predict_all(x, prompt) if self.risk_model is not None else {}
        candidates = []
        simple_prompt_prior = self._has_simple_prompt_prior(prompt, evidence_obj, evaluation_type)

        abstain_probability = float(sufficiency_probabilities.get("abstain", 0.0))
        if evaluation_type in {"required_clarification", "refusal_check"}:
            abstain_probability = max(abstain_probability, 0.85)
        candidates.append(
            {
                "model_id": "abstain",
                "action_type": "abstain",
                "cost": 0.0,
                "distance": 0.0,
                "radius": 0.0,
                "normalized_distance": 0.0,
                "pass_probability": round(abstain_probability, 6),
                "sufficiency_probability": round(abstain_probability, 6),
                "feasible": abstain_probability >= self.abstain_thresholds.get(tier, 0.55),
                "sample_count": 0,
            }
        )

        for model_id in MODEL_ORDER:
            envelope = self.envelopes[model_id]
            distance = envelope.distance(x)
            radius_multiplier = tier_radius.get(model_id, 1.0)
            feasible = envelope.contains(x, radius_multiplier)
            normalized_distance = distance / max(envelope.radius * radius_multiplier, 1e-9)
            candidates.append(
                {
                    "model_id": model_id,
                    "action_type": "model_call",
                    "cost": self.model_costs.get(model_id, 0.0),
                    "distance": round(distance, 6),
                    "radius": round(envelope.radius * radius_multiplier, 6),
                    "normalized_distance": round(normalized_distance, 6),
                    "pass_probability": round(float(pass_probabilities.get(model_id, 0.0)), 6),
                    "sufficiency_probability": round(float(sufficiency_probabilities.get(model_id, 0.0)), 6),
                    "feasible": bool(feasible),
                    "sample_count": envelope.sample_count,
                }
            )

        selected = None
        reason = ""
        abstain_candidate = candidates[0]
        if abstain_candidate["feasible"]:
            selected = "abstain"
            reason = "abstain_probability"

        if selected is None and simple_prompt_prior:
            selected = "cheap"
            reason = "simple_prompt_prior"

        pass_threshold = self.pass_thresholds.get(tier, DEFAULT_PASS_THRESHOLDS[tier])
        for candidate in candidates[1:]:
            if selected is not None:
                break
            if candidate["pass_probability"] >= pass_threshold:
                selected = candidate["model_id"]
                reason = "cheapest_passing_probability"
                break
            if candidate["feasible"]:
                selected = candidate["model_id"]
                reason = "cheapest_feasible_envelope"
                break

        if selected is None:
            max_cost = max(self.model_costs.values()) if self.model_costs else 1.0
            cost_weight = self.fallback_cost_weight.get(tier, 0.0)
            selected_candidate = min(
                candidates[1:],
                key=lambda item: (
                    item["normalized_distance"] + cost_weight * (item["cost"] / max_cost),
                    item["cost"],
                ),
            )
            selected = selected_candidate["model_id"]
            reason = "nearest_envelope_fallback"

        frontier_hint = best_under_budget(self.frontier, BUDGET_LIMITS[tier])
        evidence = self.extractor.explain(prompt, task_type, difficulty, risk_level, evaluation_type)
        evidence["simple_prompt_prior"] = 1.0 if simple_prompt_prior else 0.0
        return RouteDecision(
            prompt=prompt,
            budget_tier=tier,
            selected_model_id=selected,
            selection_reason=reason,
            evidence=evidence,
            candidates=candidates,
            frontier_hint=frontier_hint,
        )

    def _has_simple_prompt_prior(self, prompt: str, evidence: object, evaluation_type: str) -> bool:
        text = str(prompt).strip()
        if not text:
            return False
        if str(evaluation_type).lower() in {"required_clarification", "refusal_check"}:
            return False
        if len(text) > 40 or "\n" in text:
            return False
        return (
            float(getattr(evidence, "condition_count", 0.0)) == 0.0
            and float(getattr(evidence, "missing_context", 0.0)) == 0.0
            and float(getattr(evidence, "code_like", 0.0)) == 0.0
        )

    def save(self, path: str | Path) -> None:
        payload = {
            "envelopes": {model: asdict(envelope) for model, envelope in self.envelopes.items()},
            "model_costs": self.model_costs,
            "frontier": self.frontier,
            "task_classifier": self.task_classifier.to_dict() if self.task_classifier is not None else None,
            "pass_model": self.pass_model.to_dict() if self.pass_model is not None else None,
            "risk_model": self.risk_model.to_dict() if self.risk_model is not None else None,
            "radius_multipliers": self.radius_multipliers,
            "fallback_cost_weight": self.fallback_cost_weight,
            "pass_thresholds": self.pass_thresholds,
            "abstain_thresholds": self.abstain_thresholds,
            "metadata": self.metadata,
        }
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "GeometricRouter":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        envelopes = {
            model: Envelope(**data)
            for model, data in payload["envelopes"].items()
        }
        return cls(
            envelopes=envelopes,
            model_costs={key: float(value) for key, value in payload["model_costs"].items()},
            frontier=payload["frontier"],
            task_classifier=TaskClassifier.from_dict(payload["task_classifier"])
            if payload.get("task_classifier") is not None
            else None,
            pass_model=PassProbabilityModel.from_dict(payload["pass_model"])
            if payload.get("pass_model") is not None
            else None,
            risk_model=SufficiencyRiskModel.from_dict(payload["risk_model"])
            if payload.get("risk_model") is not None
            else None,
            radius_multipliers=payload.get("radius_multipliers"),
            fallback_cost_weight=payload.get("fallback_cost_weight"),
            pass_thresholds=payload.get("pass_thresholds"),
            abstain_thresholds=payload.get("abstain_thresholds"),
            metadata=payload.get("metadata", {}),
        )


