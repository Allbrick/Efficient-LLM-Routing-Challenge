from pathlib import Path

import pandas as pd

from scripts.serve_router_viewer import RouterService


def test_router_feedback_cases_match_expected_models():
    feedback_path = Path("../data/public/router_feedback.csv")
    if not feedback_path.exists():
        return

    feedback = pd.read_csv(feedback_path).fillna("")
    service = RouterService(Path("artifacts"))

    failures = []
    for row in feedback.itertuples(index=False):
        result = service.route(row.prompt, row.budget_tier)
        predicted = result["selected_model_id"]
        if predicted != row.expected_model:
            failures.append(
                f"{row.case_id}: tier={row.budget_tier} "
                f"expected={row.expected_model} predicted={predicted} "
                f"prompt={row.prompt}"
            )

    assert not failures, "\n".join(failures)
