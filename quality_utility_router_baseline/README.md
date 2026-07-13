# Quality Utility Router Baseline

This folder contains the previous router implementation: a quality-prediction
router that calibrates candidate model quality, applies prompt priors, then
selects the candidate with the best budget-tier utility.

It is kept as a runnable baseline while the repository root is used for the
next router design. Shared challenge material such as `PROJECT.md` and `data/`
stays at the repository root because it applies to both the baseline and the
new implementation.

## Run From This Folder

Open a terminal in `quality_utility_router_baseline` before running the
commands below.

```powershell
pip install -r requirements.txt
python -m pytest -q
```

## Rebuild The Legacy Pipeline

```powershell
python -m training.01_data_validation --data_path ../data/public/example_train.csv
python -m training.02_oracle_analysis --data_path ../data/public/example_train.csv
python -m training.03_train_oof --data_path ../data/public/example_train.csv
python -m training.04_calibration --oof_path artifacts/oof_predictions.csv
python -m training.05_lambda_optimize --data_path ../data/public/example_train.csv
python -m training.06_final_build --data_path ../data/public/example_train.csv --best_iteration 64
python -m training.07_feedback_tune
python scripts/build_viewer_data.py
```

## Run The Viewer

```powershell
python scripts/serve_router_viewer.py --port 4003
```

Then open:

```text
http://127.0.0.1:4003/
```

## Current Design Status

This version is useful as a working baseline, but it should not be the
foundation for the next implementation. The main limitation is that routing is
still driven by a small training set plus manual prompt priors and feedback
rules. The next router should move the decision boundary toward objective
evaluators, pass/fail evidence, and explicit budget-aware risk handling.
