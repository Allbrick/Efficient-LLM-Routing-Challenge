from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)


def _request_json(router_server_url: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    url = f"{router_server_url.rstrip('/')}{path}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
        except json.JSONDecodeError:
            body = {"error": "router_server_http_error", "message": str(exc)}
        return exc.code, body
    except (urllib.error.URLError, TimeoutError) as exc:
        return 502, {"error": "router_server_unreachable", "message": str(exc)}


def make_handler(viewer_dir: Path, router_server_url: str):
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
            if urlparse(self.path).path == "/api/config":
                status, payload = _request_json(router_server_url, "/api/config")
                self._send_json(status, payload)
                return
            super().do_GET()

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path not in {"/api/route", "/api/evaluate_csv", "/api/train_csv", "/api/feedback"}:
                self._send_json(404, {"error": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except json.JSONDecodeError as exc:
                self._send_json(400, {"error": "invalid_json", "message": str(exc)})
                return
            status, response_payload = _request_json(router_server_url, path, payload)
            self._send_json(status, response_payload)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="공통 viewer를 제공하고 라우터 서버로 API를 프록시합니다.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4010)
    parser.add_argument("--router_server_url", default="http://127.0.0.1:4100")
    parser.add_argument("--viewer_dir", default="routing_stack/viewer")
    args = parser.parse_args()

    viewer_dir = Path(args.viewer_dir).resolve()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(viewer_dir, args.router_server_url))
    print(f"뷰어 서버 주소: http://{args.host}:{args.port}/")
    print(f"라우터 서버 연결: {args.router_server_url}")
    server.serve_forever()


if __name__ == "__main__":
    main()
