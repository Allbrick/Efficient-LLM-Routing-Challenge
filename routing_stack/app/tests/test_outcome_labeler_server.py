from __future__ import annotations

import csv

from routing_stack.ai.local_ai import LocalAI, ModelConfig
from routing_stack.app.outcome_labeler_server import OutcomeLabelerApp


def test_outcome_labeler_run_all_uses_three_model_slots():
    ai = LocalAI(provider="mock", model_config=ModelConfig(cheap="c", mid="m", premium="p"))
    app = OutcomeLabelerApp(ai=ai, output_path="unused.csv")

    result = app.run_all({"prompt": "테스트 프롬프트"})

    assert sorted(result["results"]) == ["cheap", "mid", "premium"]
    assert result["results"]["cheap"]["output"] == "[mock:c] 테스트 프롬프트"
    assert result["results"]["mid"]["output"] == "[mock:m] 테스트 프롬프트"
    assert result["results"]["premium"]["output"] == "[mock:p] 테스트 프롬프트"


def test_outcome_labeler_save_review_appends_csv(tmp_path):
    path = tmp_path / "reviewed_outcome_matrix.csv"
    ai = LocalAI(provider="mock")
    app = OutcomeLabelerApp(ai=ai, output_path=path)

    result = app.save_review(
        {
            "prompt": "설명해줘",
            "outputs": {"cheap": "a", "mid": "b", "premium": "c"},
            "best_model": "premium",
            "budget_tier": "premium",
            "cheap_score": 0.2,
            "cheap_pass": False,
            "mid_score": 0.7,
            "mid_pass": False,
            "premium_score": 1.0,
            "premium_pass": True,
            "min_sufficient_model": "premium",
        }
    )

    assert result["status"] == "appended"
    assert result["prompt_id"] == "r001"
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert rows[0]["prompt_id"] == "r001"
    assert rows[0]["best_model"] == "premium"
    assert rows[0]["premium_output"] == "c"
