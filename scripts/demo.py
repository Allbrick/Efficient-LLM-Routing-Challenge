"""One-command demo runner for the geometric LLM router.

심사자와 시연자가 명령 하나로 라우터를 확인할 수 있도록 개별 스크립트를 하나의
CLI로 묶는다. `viewer`를 제외한 모든 경로는 외부 네트워크 없이 실행된다.

    python scripts/demo.py              # doctor -> test -> sim -> showcase
    python scripts/demo.py doctor       # 실행 환경과 artifact 점검
    python scripts/demo.py route "..."  # 프롬프트 하나를 라우팅하고 근거 출력
    python scripts/demo.py showcase     # 핵심 강점 시나리오 일괄 시연
    python scripts/demo.py sim          # public set 시뮬레이션
    python scripts/demo.py test         # 관련 pytest 전체 실행
    python scripts/demo.py viewer       # 브라우저 시연 (서버 2개 자동 기동)
    python scripts/demo.py full         # 학습부터 제출 검증까지 전체 재현
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import webbrowser
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

ARTIFACT_PATH = "artifacts/geometric_router.json"
SIMULATION_PATH = "artifacts/geometric_simulation.json"
CHECK_REPORT_PATH = "docs/report_assets/submission_check_run.json"
TIERS = ("fast", "balanced", "premium")

TEST_PATHS = [
    "routing_stack/app/tests",
    "routing_stack/adapters/tests",
    "routing_stack/input/tests",
    "routing_stack/training/tests",
    "router_impls/geometric/tests",
]

REQUIRED_PACKAGES = ["numpy", "pandas", "sklearn", "scipy", "joblib", "pytest"]

REQUIRED_DATA = [
    "data/public/example_train.csv",
    "data/public/example_eval_specs.csv",
]

DEFAULT_EVIDENCE_KEYS = [
    "difficulty_score",
    "risk_score",
    "code_like",
    "missing_context",
    "repetition_ratio",
    "ood_score",
]

# 시연 시나리오. 각 항목이 라우터의 서로 다른 강점을 하나씩 보여준다.
SHOWCASE = [
    {
        "label": "단순 계산",
        "prompt": "2 + 3은 얼마야?",
        "tier": "fast",
        "expect": "저비용 모델로 충분",
    },
    {
        "label": "반복 입력",
        "prompt": " ".join(["원피스 세계관에 대해 철학적 물음을 던져줘"] * 12),
        "tier": "fast",
        "expect": "표면 길이에 속지 않고 저비용 유지",
        "highlight": ["repetition_ratio", "compressed_length_norm", "length_norm"],
    },
    {
        "label": "짧지만 어려운 요청",
        "prompt": "P=NP 여부를 증명하고 그 증명의 한계를 논해줘.",
        "tier": "balanced",
        "expect": "길이가 아닌 난이도로 상향",
    },
    {
        "label": "구현+검증 요구",
        "prompt": (
            "LRU 캐시를 Python으로 구현하고, 시간복잡도를 증명한 뒤 "
            "동시성 환경의 race condition 처리 방안까지 코드로 제시해줘."
        ),
        "tier": "balanced",
        "expect": "코드성/조건 수 신호 반영",
        "highlight": ["code_like", "condition_count", "difficulty_score"],
    },
    {
        "label": "동일 요청",
        "prompt": "마이크로서비스 전환 전략을 단계별로 설계하고 리스크를 분석해줘.",
        "tier": "fast",
        "expect": "예산 제약으로 고비용 모델 제한",
    },
    {
        "label": "동일 요청",
        "prompt": "마이크로서비스 전환 전략을 단계별로 설계하고 리스크를 분석해줘.",
        "tier": "premium",
        "expect": "같은 프롬프트, 다른 feasible region",
    },
]


# --------------------------------------------------------------------------- #
# output helpers
# --------------------------------------------------------------------------- #

def _enable_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def head(title: str) -> None:
    print()
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)


def ok(message: str) -> None:
    print(f"  [ OK ] {message}")


def fail(message: str) -> None:
    print(f"  [FAIL] {message}")


def warn(message: str) -> None:
    print(f"  [WARN] {message}")


def info(message: str) -> None:
    print(f"         {message}")


def shorten(text: str, width: int = 58) -> str:
    flat = " ".join(str(text).split())
    return flat if len(flat) <= width else flat[: width - 1] + "..."


# --------------------------------------------------------------------------- #
# doctor
# --------------------------------------------------------------------------- #

def cmd_doctor(_args: argparse.Namespace) -> int:
    head("환경 점검 (doctor)")
    failures = 0

    version = sys.version_info
    if version >= (3, 12):
        ok(f"Python {version.major}.{version.minor}.{version.micro}")
    else:
        fail(f"Python {version.major}.{version.minor} - 3.12 이상이 필요합니다.")
        failures += 1

    for package in REQUIRED_PACKAGES:
        try:
            __import__(package)
        except ImportError:
            fail(f"{package} 미설치 - pip install -r requirements.txt 실행 필요")
            failures += 1
        else:
            ok(package)

    artifact = Path(ARTIFACT_PATH)
    if artifact.is_file():
        ok(f"학습 artifact ({ARTIFACT_PATH}, {artifact.stat().st_size / 1024:,.0f} KB)")
    else:
        fail(f"학습 artifact 없음 - python scripts/demo.py full 로 재생성하세요.")
        failures += 1

    for path in REQUIRED_DATA:
        if Path(path).is_file():
            ok(f"공개 데이터 {path}")
        else:
            fail(f"공개 데이터 누락: {path}")
            failures += 1

    if failures == 0:
        try:
            from router_impls.geometric.submission import create_router

            decision = create_router().route(prompt="테스트 프롬프트", budget_tier="balanced")
            ok(f"submission 진입점 정상 동작 (action={decision['action']['type']})")
        except Exception as exc:  # pragma: no cover - 진단 목적
            fail(f"submission 진입점 오류: {type(exc).__name__}: {exc}")
            failures += 1

    print()
    if failures:
        fail(f"{failures}건의 문제가 있습니다.")
    else:
        ok("모든 점검 통과 - 바로 시연할 수 있습니다.")
    return 1 if failures else 0


# --------------------------------------------------------------------------- #
# route / showcase
# --------------------------------------------------------------------------- #

def _load_router():
    from router_impls.geometric.router import GeometricRouter

    return GeometricRouter.load(ARTIFACT_PATH)


def _print_decision(decision, highlight: list[str] | None = None, verbose: bool = False) -> None:
    evidence = decision.evidence or {}
    print(f"  프롬프트   : {shorten(decision.prompt, 60)}")
    print(f"  예산 tier  : {decision.budget_tier}")
    print(f"  결정       : {decision.action_type} -> {decision.selected_model_id}")
    print(f"  선택 근거  : {decision.selection_reason}")
    if evidence.get("pre_route_lane"):
        print(
            f"  pre-route  : {evidence['pre_route_lane']} "
            f"({evidence.get('pre_route_reason', '-')})"
        )

    print()
    print(f"    {'model':<9}{'cost':>8}{'dist/rad':>10}{'pass':>8}{'suff':>8}  feasible")
    print(f"    {'-' * 9}{'-' * 8:>8}{'-' * 10:>10}{'-' * 8:>8}{'-' * 8:>8}  {'-' * 8}")
    for candidate in decision.candidates or []:
        print(
            f"    {candidate.get('model_id', '-'):<9}"
            f"{candidate.get('cost', 0.0):>8.3f}"
            f"{candidate.get('normalized_distance', 0.0):>10.2f}"
            f"{candidate.get('pass_probability', 0.0):>8.3f}"
            f"{candidate.get('sufficiency_probability', 0.0):>8.3f}"
            f"  {'yes' if candidate.get('feasible') else 'no'}"
        )

    shown = [(key, evidence[key]) for key in (highlight or DEFAULT_EVIDENCE_KEYS) if key in evidence]
    if shown:
        print()
        print("  주요 evidence")
        for key, value in shown:
            formatted = f"{value:.4f}" if isinstance(value, float) else str(value)
            print(f"    {key:<28}{formatted:>12}")

    if verbose:
        print()
        print(json.dumps(asdict(decision), ensure_ascii=False, indent=2))


def cmd_route(args: argparse.Namespace) -> int:
    head(f"단일 프롬프트 라우팅 ({args.tier})")
    router = _load_router()
    started = time.perf_counter()
    decision = router.route(args.prompt, budget_tier=args.tier)
    elapsed_ms = (time.perf_counter() - started) * 1000
    _print_decision(decision, verbose=args.verbose)
    print()
    info(f"결정 소요 시간: {elapsed_ms:.2f} ms (로컬 CPU, 외부 호출 없음)")
    return 0


def cmd_showcase(args: argparse.Namespace) -> int:
    head("시연 시나리오 (showcase)")
    router = _load_router()
    router.route("warm up", budget_tier="balanced")  # 첫 호출의 lazy 초기화 비용 제외
    rows = []

    for index, case in enumerate(SHOWCASE, start=1):
        print()
        print(f"  [{index}/{len(SHOWCASE)}] {case['label']} ({case['tier']} tier) - {case['expect']}")
        print("  " + "-" * 68)
        started = time.perf_counter()
        decision = router.route(case["prompt"], budget_tier=case["tier"])
        elapsed_ms = (time.perf_counter() - started) * 1000
        _print_decision(decision, highlight=case.get("highlight"), verbose=args.verbose)
        print()
        info(f"결정 소요 시간: {elapsed_ms:.2f} ms")
        rows.append((case["label"], case["tier"], decision.selected_model_id, elapsed_ms))

    head("시연 요약")
    for label, tier, model, elapsed_ms in rows:
        print(f"  - {label} / {tier} tier -> {model} ({elapsed_ms:.2f} ms)")
    print()
    info("동일 프롬프트라도 tier에 따라 선택이 달라지는지, 반복 입력에서")
    info("저비용 모델이 유지되는지를 위 결과에서 바로 확인할 수 있습니다.")
    return 0


# --------------------------------------------------------------------------- #
# sim / test / full
# --------------------------------------------------------------------------- #

def _run(command: list[str], title: str) -> int:
    head(title)
    info("$ " + " ".join(command))
    print()
    return subprocess.call(command, cwd=PROJECT_ROOT)


def _print_sim_summary(path: Path) -> None:
    if not path.is_file():
        warn(f"시뮬레이션 결과 파일을 찾지 못했습니다: {path}")
        return

    payload = json.loads(path.read_text(encoding="utf-8"))
    tiers = payload.get("tiers") or {}
    if not isinstance(tiers, dict) or not tiers:
        return

    head("tier별 요약")
    print(
        f"  {'tier':<12}{'quality':>9}{'cost':>9}{'over_limit':>12}"
        f"{'under':>8}{'over':>7}{'abstain':>9}"
    )
    print("  " + "-" * 66)
    for tier in TIERS:
        summary = tiers.get(tier)
        if not isinstance(summary, dict):
            continue
        counts = summary.get("selection_counts") or {}
        print(
            f"  {tier:<12}"
            f"{summary.get('mean_quality', 0.0):>9.3f}"
            f"{summary.get('mean_cost', 0.0):>9.3f}"
            f"{summary.get('cost_over_limit', 0):>12}"
            f"{summary.get('under_route', 0):>8}"
            f"{summary.get('over_route', 0):>7}"
            f"{counts.get('abstain', 0):>9}"
        )

    score = payload.get("weighted_score")
    if score is not None:
        print()
        info(f"overall weighted score: {score}")


def cmd_sim(_args: argparse.Namespace) -> int:
    code = _run(
        [
            sys.executable,
            "router_impls/geometric/scripts/simulate_geometric_router.py",
            "--artifact",
            ARTIFACT_PATH,
            "--output",
            SIMULATION_PATH,
        ],
        "public set 시뮬레이션 (sim)",
    )
    if code != 0:
        return code
    _print_sim_summary(Path(SIMULATION_PATH))
    return 0


def cmd_test(_args: argparse.Namespace) -> int:
    return _run([sys.executable, "-m", "pytest", *TEST_PATHS, "-q"], "자동화 테스트 (test)")


def cmd_full(args: argparse.Namespace) -> int:
    command = [
        sys.executable,
        "scripts/run_submission_checks.py",
        "--full",
        "--output",
        CHECK_REPORT_PATH,
    ]
    if args.strict:
        command.append("--strict-readiness")
    code = _run(command, "전체 재현 및 제출 검증 (full)")

    report = Path(CHECK_REPORT_PATH)
    if report.is_file():
        try:
            status = json.loads(report.read_text(encoding="utf-8")).get("status")
        except json.JSONDecodeError:
            status = None
        print()
        if status == "passed":
            ok(f"status=passed - {CHECK_REPORT_PATH}")
        elif status:
            warn(f"status={status} - {CHECK_REPORT_PATH} 내용을 확인하세요.")
    return code


# --------------------------------------------------------------------------- #
# viewer
# --------------------------------------------------------------------------- #

def _wait_for_port(host: str, port: int, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.5)
            if probe.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.3)
    return False


def cmd_viewer(args: argparse.Namespace) -> int:
    head("브라우저 시연 (viewer)")
    host = "127.0.0.1"
    processes: list[tuple[str, subprocess.Popen]] = []

    plan = [
        (
            "router",
            args.router_port,
            [
                sys.executable,
                "routing_stack/app/router_server.py",
                "--host", host,
                "--port", str(args.router_port),
                "--ai", args.ai,
            ],
        ),
        (
            "viewer",
            args.viewer_port,
            [
                sys.executable,
                "routing_stack/app/viewer_server.py",
                "--host", host,
                "--port", str(args.viewer_port),
                "--router_server_url", f"http://{host}:{args.router_port}",
            ],
        ),
    ]

    try:
        for name, port, command in plan:
            info("$ " + " ".join(command))
            processes.append((name, subprocess.Popen(command, cwd=PROJECT_ROOT)))
            if not _wait_for_port(host, port):
                fail(f"{name}_server가 {port} 포트에서 응답하지 않습니다.")
                return 1
            ok(f"{name}_server 기동 (port={port})")

        url = f"http://{host}:{args.viewer_port}/"
        print()
        print(f"  브라우저에서 열기: {url}")
        if args.ai == "mock":
            info("--ai mock: Ollama 없이 라우팅 결정만 시연합니다.")
        else:
            info("--ai ollama: qwen3:4b-instruct / qwen3:8b / qwen3:14b 필요")
        print()
        info("종료하려면 Ctrl+C 를 누르세요.")

        if not args.no_browser:
            webbrowser.open(url)

        while True:
            for name, process in processes:
                if process.poll() is not None:
                    fail(f"{name}_server가 예기치 않게 종료되었습니다 (code={process.returncode}).")
                    return 1
            time.sleep(0.5)
    except KeyboardInterrupt:
        print()
        info("시연을 종료합니다.")
        return 0
    finally:
        for name, process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                info(f"{name}_server 종료")


# --------------------------------------------------------------------------- #
# default pipeline
# --------------------------------------------------------------------------- #

def cmd_all(args: argparse.Namespace) -> int:
    head("기본 데모 (doctor -> test -> sim -> showcase)")
    info("네트워크와 GPU 없이 전 과정이 로컬에서 실행됩니다.")

    if cmd_doctor(args) != 0:
        fail("환경 점검에 실패해 이후 단계를 건너뜁니다.")
        return 1
    if not args.skip_test and cmd_test(args) != 0:
        fail("테스트 실패 - 이후 단계를 건너뜁니다.")
        return 1
    if cmd_sim(args) != 0:
        return 1
    return cmd_showcase(args)


# --------------------------------------------------------------------------- #
# entrypoint
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python scripts/demo.py",
        description="geometric LLM router 데모 및 검증 러너",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--verbose", action="store_true", help="decision 전체 JSON 출력")
    parser.add_argument("--skip-test", action="store_true", help="기본 실행에서 pytest 생략")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("doctor", help="실행 환경과 artifact 점검").set_defaults(func=cmd_doctor)

    route_parser = subparsers.add_parser("route", help="프롬프트 하나를 라우팅하고 근거 출력")
    route_parser.add_argument("prompt")
    route_parser.add_argument("--tier", default="balanced", choices=TIERS)
    route_parser.set_defaults(func=cmd_route)

    subparsers.add_parser("showcase", help="핵심 강점 시나리오 일괄 시연").set_defaults(func=cmd_showcase)
    subparsers.add_parser("sim", help="public set 시뮬레이션 실행").set_defaults(func=cmd_sim)
    subparsers.add_parser("test", help="관련 pytest 전체 실행").set_defaults(func=cmd_test)

    viewer_parser = subparsers.add_parser("viewer", help="router+viewer 서버를 함께 기동")
    viewer_parser.add_argument("--ai", default="mock", choices=["mock", "ollama"])
    viewer_parser.add_argument("--router-port", type=int, default=4100)
    viewer_parser.add_argument("--viewer-port", type=int, default=4010)
    viewer_parser.add_argument("--no-browser", action="store_true")
    viewer_parser.set_defaults(func=cmd_viewer)

    full_parser = subparsers.add_parser("full", help="학습부터 제출 검증까지 전체 재현")
    full_parser.add_argument("--strict", action="store_true")
    full_parser.set_defaults(func=cmd_full)

    return parser


def main() -> int:
    _enable_utf8()
    args = build_parser().parse_args()
    return getattr(args, "func", cmd_all)(args)


if __name__ == "__main__":
    raise SystemExit(main())
