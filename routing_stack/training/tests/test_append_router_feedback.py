from __future__ import annotations

import csv

from scripts.append_router_feedback import RouterFeedback, append_feedback


def test_append_router_feedback_writes_header_and_row(tmp_path):
    output = tmp_path / "online_feedback.csv"
    feedback = RouterFeedback(
        timestamp="2026-07-27T00:00:00+00:00",
        prompt="이 라우팅은 틀렸어",
        budget_tier="fast",
        selected_model_id="cheap",
        selection_reason="simple_prompt_prior",
        action_type="call_model",
        was_wrong="true",
        expected_model_id="mid",
        user_note="cheap 답변이 너무 얕음",
    )

    append_feedback(output, feedback)

    with output.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert rows[0]["prompt"] == "이 라우팅은 틀렸어"
    assert rows[0]["selected_model_id"] == "cheap"
    assert rows[0]["expected_model_id"] == "mid"
