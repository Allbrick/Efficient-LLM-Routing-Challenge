from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from routing_stack.adapters.contract import RouteRequest, RouterAdapter
from routing_stack.adapters.registry import available_routers, create_router
from routing_stack.ai.local_ai import LocalAI, ModelConfig
from routing_stack.input import normalize_input


class RouterServerApp:
    def __init__(self, routers: dict[str, RouterAdapter], ai: LocalAI, default_router: str = "geometric"):
        if default_router not in routers:
            raise ValueError(f"기본 라우터가 로드되지 않았습니다: {default_router}")
        self.routers = routers
        self.ai = ai
        self.default_router = default_router

    @classmethod
    def load(cls, router_names: list[str], ai: LocalAI, default_router: str = "geometric") -> "RouterServerApp":
        routers = {name: create_router(name) for name in router_names}
        return cls(routers=routers, ai=ai, default_router=default_router)

    def config(self) -> dict:
        return {
            "routers": sorted(self.routers),
            "default_router": self.default_router,
            "ai_provider": self.ai.provider,
            "models": self.ai.model_config.__dict__,
        }

    def route_and_run(self, payload: dict) -> dict:
        normalized = normalize_input(payload)
        prompt = normalized.text
        input_features = normalized.router_features
        router_name = str(payload.get("router", self.default_router)).strip().lower().replace("-", "_")
        if router_name not in self.routers:
            raise ValueError(f"알 수 없는 라우터입니다: {router_name}")
        request = RouteRequest(
            prompt=prompt,
            tier=str(payload.get("tier", "balanced")).lower(),
            task_type=str(payload.get("task_type", "")),
            difficulty=str(payload.get("difficulty", "")),
            risk_level=str(payload.get("risk_level", "")),
            evaluation_type=str(payload.get("evaluation_type", "")),
            input_features=input_features,
        )
        route_result = self.routers[router_name].route(request)
        ai_result = self.ai.run(route_result.model_slot, prompt)
        return {
            "input": {**request.__dict__, "router": router_name, "normalized": normalized.to_dict()},
            "router": route_result.to_dict(),
            "ai": ai_result.to_dict(),
        }


def make_handler(app: RouterServerApp):
    class Handler(SimpleHTTPRequestHandler):
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
            self._send_json(404, {"error": "not_found"})

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/api/route":
                self._send_json(404, {"error": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                self._send_json(200, app.route_and_run(payload))
            except Exception as exc:
                self._send_json(400, {"error": type(exc).__name__, "message": str(exc)})

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="모든 라우터 adapter와 AI 실행 계층을 제공하는 라우터 서버입니다.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4100)
    parser.add_argument("--routers", default=",".join(available_routers()))
    parser.add_argument("--default_router", default="geometric")
    parser.add_argument("--ai", default="ollama", choices=["ollama", "mock"])
    parser.add_argument("--ollama_url", default="http://127.0.0.1:11434")
    parser.add_argument("--cheap_model", default="qwen3:4b-instruct")
    parser.add_argument("--mid_model", default="qwen3:8b")
    parser.add_argument("--premium_model", default="qwen3:14b")
    args = parser.parse_args()

    model_config = ModelConfig(cheap=args.cheap_model, mid=args.mid_model, premium=args.premium_model)
    ai = LocalAI(provider=args.ai, model_config=model_config, base_url=args.ollama_url)
    router_names = [name.strip() for name in args.routers.split(",") if name.strip()]
    app = RouterServerApp.load(router_names=router_names, ai=ai, default_router=args.default_router)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(app))
    print(f"라우터 서버 주소: http://{args.host}:{args.port}/")
    print(f"로드된 라우터: {', '.join(sorted(app.routers))}")
    print(f"AI: {ai.provider} {model_config}")
    server.serve_forever()


if __name__ == "__main__":
    main()
