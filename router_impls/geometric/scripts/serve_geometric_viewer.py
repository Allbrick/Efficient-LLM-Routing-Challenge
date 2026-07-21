from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from router_impls.geometric.router import GeometricRouter
from router_impls.geometric.budget_allocator import allocate_public_budget
from router_impls.geometric.simulator import simulate_public_set


class GeometricRouterService:
    def __init__(self, artifact: Path, train_path: Path, specs_path: Path):
        self.router = GeometricRouter.load(artifact)
        self.train_df = pd.read_csv(train_path)
        self.specs_df = pd.read_csv(specs_path) if specs_path.exists() else pd.DataFrame()
        self._simulation_cache: dict | None = None
        self._allocation_cache: dict[str, dict] = {}

    def route(self, payload: dict) -> dict:
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            raise ValueError("prompt_required")
        tier = str(payload.get("tier", "balanced")).lower()
        decision = self.router.route(
            prompt,
            budget_tier=tier,
            task_type=str(payload.get("task_type", "")),
            difficulty=str(payload.get("difficulty", "")),
            risk_level=str(payload.get("risk_level", "")),
            evaluation_type=str(payload.get("evaluation_type", "")),
        )
        return asdict(decision)

    def simulation(self) -> dict:
        if self._simulation_cache is None:
            self._simulation_cache = simulate_public_set(self.router, self.train_df, self.specs_df)
        return self._simulation_cache

    def allocation(self, tier: str) -> dict:
        tier = tier.lower()
        if tier not in self._allocation_cache:
            self._allocation_cache[tier] = allocate_public_budget(self.router, self.train_df, self.specs_df, tier)
        return self._allocation_cache[tier]


def make_handler(viewer_dir: Path, service: GeometricRouterService):
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

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/simulation":
                self._send_json(200, service.simulation())
                return
            if parsed.path == "/api/allocation":
                params = dict(item.split("=", 1) for item in parsed.query.split("&") if "=" in item)
                self._send_json(200, service.allocation(params.get("tier", "fast")))
                return
            super().do_GET()

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/api/route":
                self._send_json(404, {"error": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                self._send_json(200, service.route(payload))
            except Exception as exc:
                self._send_json(400, {"error": type(exc).__name__, "message": str(exc)})

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the geometric router viewer.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4010)
    parser.add_argument("--artifact", default="artifacts/geometric_router.json")
    parser.add_argument("--train_path", default="data/public/example_train.csv")
    parser.add_argument("--specs_path", default="data/public/example_eval_specs.csv")
    parser.add_argument("--viewer_dir", default="router_impls/geometric/viewer")
    args = parser.parse_args()

    service = GeometricRouterService(Path(args.artifact), Path(args.train_path), Path(args.specs_path))
    handler = make_handler(Path(args.viewer_dir).resolve(), service)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Geometric router viewer: http://{args.host}:{args.port}/")
    server.serve_forever()


if __name__ == "__main__":
    main()


