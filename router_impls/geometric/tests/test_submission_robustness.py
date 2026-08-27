"""Private-simulator adapter must degrade gracefully, never raise.

A single exception inside the simulator loop would void the whole evaluation
run, so the adapter normalizes hostile input and falls back to a cheap call.
"""

from copy import deepcopy
from functools import lru_cache
from pathlib import Path

import pandas as pd

from router_impls.geometric.router import GeometricRouter
from router_impls.geometric.submission import (
    DEFAULT_BUDGET_TIER,
    FALLBACK_MODEL_ID,
    RouterSubmission,
    create_router,
    normalize_budget_tier,
    resolve_artifact_path,
)


DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "public"
VALID_ACTION_TYPES = {"call_model", "select_output", "abstain"}


@lru_cache(maxsize=1)
def cached_router():
    train_df = pd.read_csv(DATA_DIR / "example_train.csv")
    specs_df = pd.read_csv(DATA_DIR / "example_eval_specs.csv")
    return GeometricRouter.fit(train_df, specs_df)


def make_submission(tmp_path) -> RouterSubmission:
    artifact = tmp_path / "router.json"
    deepcopy(cached_router()).save(artifact)
    return RouterSubmission(artifact)


def assert_valid_payload(payload):
    assert payload["action"]["type"] in VALID_ACTION_TYPES
    assert "selected_model_id" in payload
    assert "selection_reason" in payload


def test_unknown_budget_tier_falls_back_to_default():
    assert normalize_budget_tier("UNKNOWN_TIER") == DEFAULT_BUDGET_TIER
    assert normalize_budget_tier(None) == DEFAULT_BUDGET_TIER
    assert normalize_budget_tier("") == DEFAULT_BUDGET_TIER
    assert normalize_budget_tier("FAST") == "fast"
    assert normalize_budget_tier("Premium") == "premium"


def test_route_survives_unknown_tier(tmp_path):
    payload = make_submission(tmp_path).route(prompt="테스트 요청", budget_tier="UNKNOWN_TIER")
    assert_valid_payload(payload)


def test_route_survives_none_prompt(tmp_path):
    payload = make_submission(tmp_path).route(prompt=None, budget_tier="fast")
    assert_valid_payload(payload)


def test_route_survives_malformed_history(tmp_path):
    submission = make_submission(tmp_path)
    for history in ({"bad": "shape"}, "not-a-list", 7, [None, 3, "x"]):
        payload = submission.route(prompt="테스트 요청", budget_tier="fast", history=history)
        assert_valid_payload(payload)


def test_history_index_points_at_original_position(tmp_path):
    submission = make_submission(tmp_path)
    payload = submission.route(
        prompt="2 + 3의 값만 숫자로 답해줘.",
        budget_tier="fast",
        history=[None, "junk", {"model_id": "cheap", "output": "5"}],
        task_type="math_exact",
        difficulty="trivial",
        risk_level="low",
        evaluation_type="exact_match",
    )
    assert payload["action"] == {
        "type": "select_output",
        "model_id": "cheap",
        "history_index": 2,
    }


def test_internal_error_degrades_to_cheap_call(tmp_path):
    submission = make_submission(tmp_path)

    def boom(**_kwargs):
        raise RuntimeError("simulated router failure")

    submission.router.route = boom
    payload = submission.route(prompt="테스트 요청", budget_tier="fast")

    assert payload["action"] == {"type": "call_model", "model_id": FALLBACK_MODEL_ID}
    assert payload["selection_reason"].startswith("fallback_on_error:")


def test_artifact_path_resolves_from_any_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    resolved = resolve_artifact_path("artifacts/geometric_router.json")
    if resolved.is_file():
        assert resolved.is_absolute()
        assert create_router(resolved).artifact_path == resolved
