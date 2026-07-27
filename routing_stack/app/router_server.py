from __future__ import annotations

import argparse
from datetime import datetime, timezone
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
from routing_stack.context import resolve_context
from routing_stack.input import normalize_input
from routing_stack.training.prompt_label_csv import model_slot_to_score, read_prompt_label_csv_text, score_to_model_slot
from routing_stack.training.train_prompt_label_router import train_from_csv
from scripts.append_router_feedback import RouterFeedback, append_feedback


def _read_label_rows(csv_text: str) -> list[dict[str, str]]:
    return read_prompt_label_csv_text(csv_text)


def _candidate_scores(route_result) -> dict[str, float | None]:
    return {candidate.model_id: candidate.score for candidate in route_result.candidates if candidate.model_id in {"cheap", "mid", "premium"}}


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
        routing_context = resolve_context(payload, normalized)
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
            context_features=routing_context.router_context,
            executor_context={
                **routing_context.executor_context,
                "model_metadata": payload.get("model_metadata"),
            },
            call_history=routing_context.session_state.previous_calls,
        )
        route_result = self.routers[router_name].route(request)
        ai_result = self.ai.run(route_result.model_slot, prompt)
        return {
            "input": {
                **request.__dict__,
                "router": router_name,
                "normalized": normalized.to_dict(),
                "routing_context": routing_context.to_dict(),
            },
            "router": route_result.to_dict(),
            "ai": ai_result.to_dict(),
        }

    def evaluate_csv(self, payload: dict) -> dict:
        router_name = str(payload.get("router", self.default_router)).strip().lower().replace("-", "_")
        tier = str(payload.get("tier", "balanced")).lower()
        rows = _read_label_rows(str(payload.get("csv_text", "") or ""))
        if router_name not in self.routers:
            raise ValueError(f"알 수 없는 라우터입니다: {router_name}")

        results = []
        bucket_correct = 0
        absolute_errors: list[float] = []
        bucket_counts: dict[str, int] = {}
        prediction_counts: dict[str, int] = {}
        for item in rows:
            expected_score = float(item["routing_score"])
            expected_bucket = score_to_model_slot(expected_score)
            route_result = self._route_only(router_name, item["prompt"], tier)
            actual = route_result.selected_model_id
            predicted_score = _predicted_routing_score(route_result)
            is_correct = actual == expected_bucket
            bucket_correct += int(is_correct)
            absolute_errors.append(abs(predicted_score - expected_score))
            bucket_counts[expected_bucket] = bucket_counts.get(expected_bucket, 0) + 1
            prediction_counts[actual] = prediction_counts.get(actual, 0) + 1
            results.append(
                {
                    "prompt": item["prompt"],
                    "expected_score": expected_score,
                    "expected": expected_bucket,
                    "predicted_score": round(predicted_score, 3),
                    "actual": actual,
                    "correct": is_correct,
                    "absolute_error": round(abs(predicted_score - expected_score), 3),
                    "selection_reason": route_result.selection_reason,
                    "candidate_scores": _candidate_scores(route_result),
                }
            )

        total = len(results)
        return {
            "router": router_name,
            "tier": tier,
            "row_count": total,
            "correct_count": bucket_correct,
            "bucket_accuracy": round(bucket_correct / max(total, 1), 6),
            "accuracy": round(bucket_correct / max(total, 1), 6),
            "mae": round(sum(absolute_errors) / max(total, 1), 6),
            "bucket_counts": bucket_counts,
            "label_counts": bucket_counts,
            "prediction_counts": prediction_counts,
            "rows": results,
        }

    def train_csv(self, payload: dict) -> dict:
        csv_text = str(payload.get("csv_text", "") or "")
        rows = _read_label_rows(csv_text)
        output_path = str(payload.get("output_path", "artifacts/prompt_label_router.joblib") or "artifacts/prompt_label_router.joblib")
        temp_path = Path("artifacts/_prompt_label_upload.csv")
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_text(csv_text, encoding="utf-8")
        summary = train_from_csv(temp_path, output_path)
        self.routers["learned_label"] = create_router("learned_label", output_path)
        summary["loaded_router"] = "learned_label"
        summary["validated_rows"] = len(rows)
        return summary

    def record_feedback(self, payload: dict) -> dict:
        prompt = str(payload.get("prompt", "") or "").strip()
        if not prompt:
            raise ValueError("prompt is required")
        output_path = str(payload.get("output_path", "data/router_feedback/online_feedback.csv") or "")
        feedback = RouterFeedback(
            timestamp=str(payload.get("timestamp", "") or datetime.now(timezone.utc).isoformat()),
            prompt=prompt,
            budget_tier=str(payload.get("budget_tier", payload.get("tier", "balanced")) or "balanced"),
            selected_model_id=str(payload.get("selected_model_id", payload.get("selected", "")) or ""),
            selection_reason=str(payload.get("selection_reason", "") or ""),
            action_type=str(payload.get("action_type", "") or ""),
            was_wrong=str(payload.get("was_wrong", "true") or "true").lower(),
            expected_model_id=str(payload.get("expected_model_id", payload.get("expected", "")) or ""),
            user_note=str(payload.get("user_note", payload.get("note", "")) or ""),
            history_model_id=str(payload.get("history_model_id", "") or ""),
            history_output=str(payload.get("history_output", "") or ""),
            evaluator_score=str(payload.get("evaluator_score", "") or ""),
            evaluator_sufficient=str(payload.get("evaluator_sufficient", "") or ""),
            escalated_to=str(payload.get("escalated_to", "") or ""),
            final_selected_model_id=str(payload.get("final_selected_model_id", "") or ""),
        )
        path = append_feedback(output_path, feedback)
        return {"status": "appended", "path": str(path)}

    def _route_only(self, router_name: str, prompt: str, tier: str):
        payload = {"prompt": prompt, "tier": tier, "router": router_name}
        normalized = normalize_input(payload)
        routing_context = resolve_context(payload, normalized)
        request = RouteRequest(
            prompt=normalized.text,
            tier=tier,
            input_features=normalized.router_features,
            context_features=routing_context.router_context,
            executor_context=routing_context.executor_context,
            call_history=routing_context.session_state.previous_calls,
        )
        return self.routers[router_name].route(request)


def _predicted_routing_score(route_result) -> float:
    diagnostics = route_result.diagnostics or {}
    if "routing_score" in diagnostics:
        try:
            return float(diagnostics["routing_score"])
        except (TypeError, ValueError):
            pass
    return model_slot_to_score(route_result.selected_model_id)


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
            path = urlparse(self.path).path
            if path not in {"/api/route", "/api/evaluate_csv", "/api/train_csv", "/api/feedback"}:
                self._send_json(404, {"error": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                if path == "/api/route":
                    self._send_json(200, app.route_and_run(payload))
                elif path == "/api/evaluate_csv":
                    self._send_json(200, app.evaluate_csv(payload))
                elif path == "/api/train_csv":
                    self._send_json(200, app.train_csv(payload))
                else:
                    self._send_json(200, app.record_feedback(payload))
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
    parser.add_argument("--ai_timeout", type=int, default=120)
    parser.add_argument("--cheap_model", default="qwen3:4b-instruct")
    parser.add_argument("--mid_model", default="qwen3:8b")
    parser.add_argument("--premium_model", default="qwen3:14b")
    args = parser.parse_args()

    model_config = ModelConfig(cheap=args.cheap_model, mid=args.mid_model, premium=args.premium_model)
    ai = LocalAI(provider=args.ai, model_config=model_config, base_url=args.ollama_url, timeout_seconds=args.ai_timeout)
    router_names = [name.strip() for name in args.routers.split(",") if name.strip()]
    app = RouterServerApp.load(router_names=router_names, ai=ai, default_router=args.default_router)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(app))
    print(f"라우터 서버 주소: http://{args.host}:{args.port}/")
    print(f"로드된 라우터: {', '.join(sorted(app.routers))}")
    print(f"AI: {ai.provider} {model_config}")
    server.serve_forever()


if __name__ == "__main__":
    main()
