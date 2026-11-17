# HepatiQ technical note

**Title:** Explainable 5-year risk estimation in primary biliary cholangitis: a research prototype report

**Status:** Research prototype; not a medical device; no external validation

**Serving model:** v1 Logistic Regression pipeline at `models/model.skops`

## Summary

HepatiQ estimates the probability of death or liver transplant within 5 years for patients already diagnosed with primary biliary cholangitis (PBC). The pipeline uses 17 routine clinical and biochemical variables, fits `IterativeImputer` and `StandardScaler` inside each cross-validation fold, and produces per-patient SHAP attributions from a linear model.

On internal out-of-fold evaluation (n=329, 132 events), ROC-AUC is 0.8828 [0.8409, 0.9185] versus a class-prior baseline of 0.4924 [0.4277, 0.5514]. On the only held-out patients available, the fixed 1989 Mayo Risk Score reached AUC 0.851 [0.749, 0.928] versus 0.816 [0.712, 0.905] for the retrained HepatiQ pipeline. The intervals overlap; HepatiQ has not demonstrated added value over the five-variable score.

## Data

- Source: canonical `survival::pbc` cohort, exported from CRAN `survival` 3.8-12 with pinned SHA-256 provenance.
- Canonical records: 418. After excluding 89 patients censored before 5 years, 329 remain.
- Outcome: death or transplant within 1,825 days.
- Class balance: 132 events (40.1%) and 197 non-events (59.9%).
- The cohort predates modern PBC treatment standards and comes from one historical trial network.

## Model

- Logistic Regression with L2 regularization and `class_weight='balanced'`.
- Selected from Logistic Regression, Random Forest, and XGBoost using a documented rule: overlapping ROC-AUC intervals are treated as a tie, then Brier score breaks the tie.
- Preprocessing: multivariate imputation and scaling fit inside each fold, never on the full dataset upfront.
- Serialization: `skops` with startup SHA-256 and 17-feature contract verification against `models/model_manifest.json`.
- Explainability: `shap.LinearExplainer`, appropriate for the winning linear model.

## Evaluation

| Estimate | Result | Reading |
| --- | ---: | --- |
| Internal OOF ROC-AUC | 0.8828 [0.8409, 0.9185] | Leakage-safe estimate on this cohort |
| Class-prior ROC-AUC | 0.4924 [0.4277, 0.5514] | Naive baseline |
| OOF Brier | 0.1364 [0.1136, 0.1632] | Calibration better than baseline but imperfect |
| Calibration slope | 0.725 | Probabilities overpredict on average |
| CITL | -0.498 | Same overprediction signal |
| ECE | 0.062 | Absolute calibration error |
| Held-out Mayo Risk Score AUC | 0.851 [0.749, 0.928] | Fixed 1989 five-variable score |
| Held-out HepatiQ AUC | 0.816 [0.712, 0.905] | v1 retrained on 312 randomized patients |

The held-out comparison uses 70 non-randomized patients with a complete Mayo Risk Score and 33 events. It is the only honest head-to-head available in this dataset. The confidence intervals overlap, so neither score is proven superior; the result shows that a 17-feature model has not demonstrated added value on held-out patients.

## Software

- Backend: FastAPI service exposing `/health`, `/predict`, `/predict/batch`, `/agent/reason`, `/stats`, and history endpoints.
- Frontend: Streamlit application with 17-input form, single-patient scorecard, local history, PDF summary, and bulk CSV scoring.
- Bulk scoring: up to 1,000 rows; per-row validation errors; results downloadable as CSV; batch rows are not written to local history.
- Rate limiting: in-memory sliding-window limit on prediction and history endpoints.

## Limitations

- No external validation; all evidence comes from the same historical Mayo cohort.
- Held-out benchmark did not show added value over the Mayo Risk Score.
- Calibration is imperfect and the model overpredicts on average.
- SHAP explains the model, not intervention effects.
- Imputed values produce imputed explanations; the UI marks them.
- No authentication, authorization, PHI controls, audit logging, or monitoring.
- MELD cannot be computed because INR and creatinine are absent.
- GLOBE and UK-PBC require external cohorts or post-UDCA treatment response.
- Not FDA-approved, CDSCO-approved, or clinically validated.

## Reproduce

From the repository root:

```bash
pip install -r requirements.txt
pip install -e . --no-deps
python -m hepatiq.validation.run_validation
python scripts/benchmark_scores.py
python -m pytest --cov=src/hepatiq --cov-fail-under=60
```

The notebook `notebooks/hepatiq_reproducibility.ipynb` wraps these commands and displays the generated report and figures.

## Attribution

V1 was a student team project at Sharda University's Anand School of Engineering & Technology. V2 research, including the published-score benchmark and survival analysis, is authored by Pranjal Dubey. See `AUTHORS.md`.

## CTA

**Read the evidence brief** at `docs/outreach/EVIDENCE_BRIEF.md` or **open the model card** at `docs/model_card.md`.
