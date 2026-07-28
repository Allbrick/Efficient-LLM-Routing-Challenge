from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from routing_stack.ai.local_ai import LocalAI, ModelConfig
from routing_stack.training.outcome_labeler import (
    MODEL_SLOTS,
    append_reviewed_outcome,
    build_reviewed_outcome_row,
)


VIEWER_ROOT = PROJECT_ROOT / "routing_stack" / "outcome_labeler_viewer"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "router_outcomes" / "reviewed_outcome_matrix.csv"


class OutcomeLabelerApp:
    def __init__(self, ai: LocalAI, output_path: str | Path = DEFAULT_OUTPUT_PATH):
        self.ai = ai
        self.output_path = Path(output_path)

    def config(self) -> dict:
        return {
            "ai_provider": self.ai.provider,
            "models": self.ai.model_config.__dict__,
            "output_path": str(self.output_path),
        }

    def run_all(self, payload: dict) -> dict:
        prompt = str(payload.get("prompt", "") or "").strip()
        if not prompt:
            raise ValueError("prompt is required")

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {slot: executor.submit(self.ai.run, slot, prompt) for slot in MODEL_SLOTS}
            results = {slot: futures[slot].result().to_dict() for slot in MODEL_SLOTS}
        return {"prompt": prompt, "results": results}

    def save_review(self, payload: dict) -> dict:
        prompt = str(payload.get("prompt", "") or "")
        best_model = str(payload.get("best_model", "") or "")
        outputs = {
            slot: str(payload.get("outputs", {}).get(slot, "") or "")
            for slot in MODEL_SLOTS
        }
        metadata = {
            key: payload.get(key, "")
            for key in ("budget_tier", "task_type", "difficulty", "risk_level", "evaluation_type", "failure_reason")
        }
        overrides = {
            key: payload.get(key)
            for key in (
                "cheap_score",
                "cheap_pass",
                "mid_score",
                "mid_pass",
                "premium_score",
                "premium_pass",
                "min_sufficient_model",
                "abstain_is_correct",
            )
            if key in payload
        }
        row = build_reviewed_outcome_row(
            path=self.output_path,
            prompt=prompt,
            outputs=outputs,
            best_model=best_model,
            metadata=metadata,
            overrides=overrides,
        )
        append_reviewed_outcome(self.output_path, row)
        return {"status": "appended", "path": str(self.output_path), "prompt_id": row["prompt_id"], "row": row}


def make_handler(app: OutcomeLabelerApp):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(VIEWER_ROOT), **kwargs)

        def _send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/api/config":
                self._send_json(200, app.config())
                return
            if path == "/api/health":
                self._send_json(200, {"ok": True})
                return
            return super().do_GET()

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path not in {"/api/run_all", "/api/save"}:
                self._send_json(404, {"error": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                if path == "/api/run_all":
                    self._send_json(200, app.run_all(payload))
                else:
                    self._send_json(200, app.save_review(payload))
            except Exception as exc:
                self._send_json(400, {"error": type(exc).__name__, "message": str(exc)})

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Ollama 3-model outcome matrix labeling viewer")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4120)
    parser.add_argument("--ai", default="ollama", choices=["ollama", "mock"])
    parser.add_argument("--ollama_url", default="http://127.0.0.1:11434")
    parser.add_argument("--ai_timeout", type=int, default=240)
    parser.add_argument("--cheap_model", default="qwen3:4b-instruct")
    parser.add_argument("--mid_model", default="qwen3:8b")
    parser.add_argument("--premium_model", default="qwen3:14b")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args()

    model_config = ModelConfig(cheap=args.cheap_model, mid=args.mid_model, premium=args.premium_model)
    ai = LocalAI(provider=args.ai, model_config=model_config, base_url=args.ollama_url, timeout_seconds=args.ai_timeout)
    app = OutcomeLabelerApp(ai=ai, output_path=args.output)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(app))
    print(f"Outcome labeler viewer: http://{args.host}:{args.port}/")
    print(f"AI: {ai.provider} {model_config}")
    print(f"Output CSV: {Path(args.output)}")
    server.serve_forever()


if __name__ == "__main__":
    main()
