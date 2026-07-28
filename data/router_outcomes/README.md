# Router Outcome Matrix

`public_outcome_matrix.csv` is the current outcome matrix generated from the public training data.

For production-grade router calibration, add a reviewed matrix with the same columns:

```csv
prompt_id,prompt,budget_tier,task_type,difficulty,risk_level,evaluation_type,cheap_output,cheap_score,cheap_pass,mid_output,mid_score,mid_pass,premium_output,premium_score,premium_pass,min_sufficient_model,best_model,premium_gain_over_mid,mid_gain_over_cheap,abstain_is_correct,failure_reason
```

User-provided rows should contain the actual outputs from cheap/mid/premium models and reviewed pass/fail or quality scores.

Train with a reviewed matrix:

```powershell
python router_impls\geometric\scripts\train_geometric_router.py --outcome_matrix_path data\router_outcomes\reviewed_outcome_matrix.csv
```
