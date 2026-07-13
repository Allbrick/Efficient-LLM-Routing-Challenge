from __future__ import annotations

import argparse
import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.calibrator import Calibrator
from src.candidate_expander import CandidateExpander
from src.data_models import CostConfig, LambdaParams
from src.feature_extractor import FeatureExtractor
from src.prompt_policy import apply_prompt_prior, estimate_prompt_complexity
from src.quality_predictor import QualityPredictor
from src.utility_engine import CostNormalizer, UtilityEngine


class RouterService:
    def __init__(self, artifacts_dir: Path):
        self.feature_extractor = FeatureExtractor.load(str(artifacts_dir / "feature_pipeline.pkl"))
        self.expander = CandidateExpander.load(str(artifacts_dir / "model_id_mapping.json"))
        self.predictor = QualityPredictor.load(str(artifacts_dir / "lgbm_model.txt"))
        self.calibrator = Calibrator.load(str(artifacts_dir / "calibration_params.json"))
        self.lambda_params = LambdaParams.load(str(artifacts_dir / "lambda_params.json"))
        self.cost_config = CostConfig.load(str(artifacts_dir / "cost_normalization.json"))
        self.utility_engine = UtilityEngine(self.lambda_params, CostNormalizer(self.cost_config))
        self.model_ids = sorted(self.expander.model_id_mapping, key=self.expander.model_id_mapping.get)

    def resolve_tier(self, prompt: str, requested_tier: str) -> tuple[str, float]:
        complexity = estimate_prompt_complexity(prompt)
        if requested_tier != "auto":
            return requested_tier, complexity
        if complexity < 0.28:
            return "fast", complexity
        if complexity < 0.62:
            return "balanced", complexity
        return "premium", complexity

    def route(self, prompt: str, tier: str = "auto") -> dict:
        resolved_tier, complexity = self.resolve_tier(prompt, tier)
        prompt_features = self.feature_extractor.transform([prompt])
        expanded, model_ids = self.expander.expand(prompt_features, self.model_ids)
        raw_q = self.predictor.predict(expanded)
        encoded = np.array([self.expander.model_id_mapping[mid] for mid in model_ids], dtype=np.int32)
        q_cal = self.calibrator.transform(raw_q, encoded)
        q_policy = apply_prompt_prior(q_cal, model_ids, prompt, resolved_tier)
        utilities = self.utility_engine.compute_utilities(q_policy, model_ids, resolved_tier)
        selected = self.utility_engine.select(q_policy, model_ids, resolved_tier)

        candidates = []
        for idx, model_id in enumerate(model_ids):
            candidates.append(
                {
                    "model_id": model_id,
                    "predicted_quality": round(float(raw_q[idx]), 6),
                    "calibrated_quality": round(float(q_cal[idx]), 6),
                    "policy_quality": round(float(q_policy[idx]), 6),
                    "cost": round(float(self.cost_config.cost_map[model_id]), 6),
                    "utility": round(float(utilities[idx]), 6),
                }
            )

        return {
            "prompt": prompt,
            "tier": tier,
            "resolved_tier": resolved_tier,
            "selected_model_id": selected,
            "prompt_complexity": round(complexity, 6),
            "lambda": self.lambda_params.get(resolved_tier),
            "candidates": candidates,
        }


def make_handler(viewer_dir: Path, service: RouterService):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(viewer_dir), **kwargs)

        def _send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/api/route":
                self._send_json(404, {"error": "not_found"})
                return

            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                prompt = str(payload.get("prompt", "")).strip()
                tier = str(payload.get("tier", "auto")).lower()
                if not prompt:
                    self._send_json(400, {"error": "prompt_required"})
                    return
                if tier not in {"auto", "fast", "balanced", "premium"}:
                    self._send_json(400, {"error": "invalid_tier"})
                    return
                self._send_json(200, service.route(prompt, tier))
            except Exception as exc:
                self._send_json(500, {"error": type(exc).__name__, "message": str(exc)})

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve router viewer with a local routing API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4003)
    parser.add_argument("--viewer_dir", default="viewer")
    parser.add_argument("--artifacts_dir", default="artifacts")
    args = parser.parse_args()

    viewer_dir = Path(args.viewer_dir).resolve()
    service = RouterService(Path(args.artifacts_dir))
    server = ThreadingHTTPServer((args.host, args.port), make_handler(viewer_dir, service))
    print(f"Router viewer: http://{args.host}:{args.port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
