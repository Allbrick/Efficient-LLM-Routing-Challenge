from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from geometric_router.envelope import Envelope, fit_envelope
from geometric_router.evaluator import build_training_labels
from geometric_router.features import MODEL_ORDER, EvidenceExtractor
from geometric_router.pareto import best_under_budget, build_pareto_frontier


BUDGET_LIMITS = {
    "fast": 0.03,
    "balanced": 0.08,
    "premium": 0.20,
}

RADIUS_MULTIPLIER = {
    "fast": 1.10,
    "balanced": 1.00,
    "premium": 0.92,
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
        metadata: dict | None = None,
    ):
        self.envelopes = envelopes
        self.model_costs = model_costs
        self.frontier = frontier
        self.metadata = metadata or {}
        self.extractor = EvidenceExtractor()

    @classmethod
    def fit(
        cls,
        train_df: pd.DataFrame,
        specs_df: pd.DataFrame | None = None,
        fallback_threshold: float = 0.85,
        radius_quantile: float = 0.90,
    ) -> "GeometricRouter":
        labels = build_training_labels(train_df, specs_df, fallback_threshold=fallback_threshold)
        merged = train_df.merge(labels, on=["prompt_id", "model_id"], how="left")
        spec_map = {}
        if specs_df is not None and not specs_df.empty:
            spec_map = {row.prompt_id: row._asdict() for row in specs_df.itertuples(index=False)}

        extractor = EvidenceExtractor()
        prompt_features = {}
        for prompt_id, group in train_df.groupby("prompt_id", sort=False):
            first = group.iloc[0]
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
        metadata = {
            "fallback_threshold": fallback_threshold,
            "radius_quantile": radius_quantile,
            "n_prompts": int(train_df["prompt_id"].nunique()),
            "n_rows": int(len(train_df)),
        }
        return cls(envelopes=envelopes, model_costs=model_costs, frontier=frontier, metadata=metadata)

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

        evidence_obj = self.extractor.transform(prompt, task_type, difficulty, risk_level, evaluation_type)
        x = evidence_obj.as_vector()
        radius_multiplier = RADIUS_MULTIPLIER[tier]
        candidates = []

        for model_id in MODEL_ORDER:
            envelope = self.envelopes[model_id]
            distance = envelope.distance(x)
            feasible = envelope.contains(x, radius_multiplier)
            normalized_distance = distance / max(envelope.radius * radius_multiplier, 1e-9)
            candidates.append(
                {
                    "model_id": model_id,
                    "cost": self.model_costs.get(model_id, 0.0),
                    "distance": round(distance, 6),
                    "radius": round(envelope.radius * radius_multiplier, 6),
                    "normalized_distance": round(normalized_distance, 6),
                    "feasible": bool(feasible),
                    "sample_count": envelope.sample_count,
                }
            )

        selected = None
        reason = ""
        for candidate in candidates:
            if candidate["feasible"]:
                selected = candidate["model_id"]
                reason = "cheapest_feasible_envelope"
                break

        if selected is None:
            selected_candidate = min(candidates, key=lambda item: (item["normalized_distance"], item["cost"]))
            selected = selected_candidate["model_id"]
            reason = "nearest_envelope_fallback"

        frontier_hint = best_under_budget(self.frontier, BUDGET_LIMITS[tier])
        return RouteDecision(
            prompt=prompt,
            budget_tier=tier,
            selected_model_id=selected,
            selection_reason=reason,
            evidence=self.extractor.explain(prompt, task_type, difficulty, risk_level, evaluation_type),
            candidates=candidates,
            frontier_hint=frontier_hint,
        )

    def save(self, path: str | Path) -> None:
        payload = {
            "envelopes": {model: asdict(envelope) for model, envelope in self.envelopes.items()},
            "model_costs": self.model_costs,
            "frontier": self.frontier,
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
            metadata=payload.get("metadata", {}),
        )
