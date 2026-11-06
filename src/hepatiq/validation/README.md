# Validation

Statistical validation for the HepatiQ model (owner: Rudra).

## What's here

- **`validate.py`** — reusable statistics: `bootstrap_ci` (deterministic percentile bootstrap, seedable) and `compare_to_meld` (model-vs-clinical-score Brier/AUC comparison, used by tests).
- **`run_validation.py`** — the validation runner: generates 5-fold out-of-fold (OOF) predictions with a fresh pipeline per fold (no leakage), scores ROC-AUC, Brier, precision, recall and F1 with 95% bootstrap CIs, and compares against a class-prior baseline.
- **`report.md`** — the committed report produced by the runner. Regenerate it with the command below; it is deterministic (folds and bootstrap both seed 42).
- **`calibration_plot.py`** — OOF reliability diagram computed from genuine 5-fold predictions, using quantile bins and bin counts. Generates `calibration_plot.png`; the generated image is not committed.

## Running

```bash
pip install -r requirements.txt   # once, from the repo root
pip install -e . --no-deps
python -m hepatiq.validation.run_validation
python -m hepatiq.validation.calibration_plot
```

Latest results (n=329, 132 events): **ROC-AUC 0.8828 [0.8409, 0.9185]** vs.
class-prior baseline 0.4924 [0.4277, 0.5514]; Brier **0.1364 [0.1136, 0.1632]**
vs. 0.2403 [0.2307, 0.2516] — the model separates clearly from the baseline on
both. OOF calibration slope is 0.725, CITL -0.498, ECE 0.062, and ICI 0.248;
reliability diagrams are in `reports/figures/`.

## Published-score benchmark

The five-variable 1989 Mayo Risk Score is computable from this cohort and is
benchmarked in [`docs/SCORE_BENCHMARK.md`](../../../docs/SCORE_BENCHMARK.md).
On held-out non-randomized patients (n=70, 33 events), Mayo AUC 0.851 vs 0.816
for retrained v1; the CIs overlap, so superiority is not demonstrated.

## Why there is no MELD benchmark

A clinical-score benchmark (MELD) needs bilirubin, INR and creatinine. The Mayo PBC dataset has bilirubin and protime, but **no INR and no creatinine**, so MELD cannot be computed from this data — a "MELD" built from protime and a fixed creatinine would be a non-clinical construct wearing a clinical name. The class-prior baseline answers the question that matters for judging the model: does it beat "always guess the cohort prevalence"? Decision recorded in `docs/ROADMAP.md`.

## Notes for contributors

- Tests for the validation helpers live in `tests/test_validation.py` and `tests/test_calibration_plot.py` (run the whole suite with `python -m pytest`).
- Keep the runner deterministic: seed every split and bootstrap, don't read anything time-dependent.
- Update `report.md` whenever the model or cohort changes, and mention it in the PR.

## Related components

- **ML** (`../ml/`) — model and preprocessing being validated
- **Backend** (`../backend/`) — API endpoints the report backs up
- **Data** (`../../../data/`) — the cohort
