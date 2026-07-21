from __future__ import annotations

import pandas as pd


def build_pareto_frontier(train_df: pd.DataFrame) -> list[dict]:
    points = (
        train_df.groupby("model_id", as_index=False)
        .agg(cost=("cost", "mean"), quality=("quality_score", "mean"))
        .sort_values(["cost", "quality"], ascending=[True, False])
    )

    frontier = []
    best_quality = float("-inf")
    for row in points.itertuples(index=False):
        quality = float(row.quality)
        if quality > best_quality:
            frontier.append(
                {
                    "model_id": row.model_id,
                    "cost": float(row.cost),
                    "quality": quality,
                }
            )
            best_quality = quality
    return frontier


def best_under_budget(frontier: list[dict], budget: float) -> dict | None:
    candidates = [point for point in frontier if point["cost"] <= budget]
    if not candidates:
        return None
    return max(candidates, key=lambda point: (point["quality"], -point["cost"]))

