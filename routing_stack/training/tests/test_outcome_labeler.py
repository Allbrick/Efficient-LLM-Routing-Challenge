from __future__ import annotations

import csv

from routing_stack.training.outcome_labeler import append_reviewed_outcome, build_reviewed_outcome_row, next_prompt_id
from routing_stack.training.outcome_matrix import OUTCOME_COLUMNS


def test_build_and_append_reviewed_outcome_row(tmp_path):
    path = tmp_path / "reviewed_outcome_matrix.csv"
    row = build_reviewed_outcome_row(
        path=path,
        prompt="안녕",
        outputs={"cheap": "cheap answer", "mid": "mid answer", "premium": "premium answer"},
        best_model="mid",
        metadata={"budget_tier": "fast", "task_type": "chat"},
    )

    assert row["prompt_id"] == "r001"
    assert row["best_model"] == "mid"
    assert row["min_sufficient_model"] == "mid"
    assert row["cheap_pass"] is False
    assert row["mid_pass"] is True
    assert list(row.keys()) == list(OUTCOME_COLUMNS)

    append_reviewed_outcome(path, row)
    assert next_prompt_id(path) == "r002"

    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert rows[0]["prompt"] == "안녕"
    assert rows[0]["best_model"] == "mid"
    assert rows[0]["mid_output"] == "mid answer"


def test_prompt_id_skips_non_review_ids(tmp_path):
    path = tmp_path / "matrix.csv"
    path.write_text("prompt_id,prompt\nr002,a\npublic_1,b\nr010,c\n", encoding="utf-8")

    assert next_prompt_id(path) == "r011"
