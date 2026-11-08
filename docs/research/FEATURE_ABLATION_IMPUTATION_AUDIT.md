# Feature Ablation and Imputation Audit

> Historical note (2026-11-08): the serving artifact moved from
> `models/model.pkl` to `models/model.skops`. The frozen base model SHA-256 below
> identifies the pre-migration pickle used by this audit.

**Protocol version:** 1.0  
**Status:** frozen; no experiments run yet  
**Frozen at:** the commit that introduces this file  
**Base commit:** `db2bf514c37f27bfbae13ab79b559350bdcee970`  
**Base model SHA-256:** `BC96BB1D7399391EA103C65515A76E5F40E8A7CFD4ACDCE27D59D935020C31F1`  
**Research branch:** `research/feature-ablation-imputation-audit`

> This document is the pre-registered protocol for the feature-ablation and
> imputation-sensitivity investigation. Results will be appended in a later
> commit. The protocol must not be changed after results are inspected. Any
> deviation is recorded as exploratory in the changelog at the end of this
> document.

## 1. Decision record

Approved scope:

1. Primary endpoint remains death or liver transplantation within five years.
2. Feature configurations: F5, F6, F16, F17, F17+IND.
3. Weighted and unweighted Logistic Regression are compared.
4. Random Forest and XGBoost remain secondary exploratory comparisons.
5. The existing 312/106 split is used exactly once, strictly after this
   protocol is frozen, and never for model selection or calibration fitting.
6. Mayo's `5.76%` probability is treated as non-comparable until its exact
   formula, baseline survival, units and endpoint are verified.
7. Survival analysis remains a separate future research protocol.
8. Production model artifacts, deployed inference code and risk thresholds
   are not modified.
9. Calibration is co-primary with feature ablation.
10. The extreme imputation sensitivity observed for Patient B is investigated
    directly.
11. The `25.00%` versus `27.48%` discrepancy is pinned by exact inputs, units,
    model hash and application version.
12. Imputation is not assumed to be the sole cause of the Mayo discrepancy.
13. All existing work is preserved.
14. The hardcoded calibration plot is documented as a critical integrity issue
    and corrected only through a separate reviewable change.

## 2. Preliminary evidence already established

These facts motivate the protocol. They were established read-only before the
protocol freeze.

### 2.1 Cohort and endpoint

- Canonical external dataset: `data/external/pbc.csv` (418 rows).
- Current processed target: `data/processed/pbc_5yr_target.csv` (329 labeled
  patients).
- Events: 132 (115 deaths, 17 transplants); 197 event-free; event rate 40.1%.
- Target: `severe_event_5yr = 1` for death or transplant within 1825 days,
  `0` for event-free at 1825 days, drop if censored before 1825 days.
- 89 patients censored before five years were dropped. All had `status = 0`;
  follow-up 691-1810 days, median 1363 days; baseline medians were similar to
  retained patients.
- No row has `time == 1825`; training and benchmark labels agree for all 329
  known labels.
- `data/raw/pbc.csv` has 419 rows; `data/external/pbc.csv` has 418. The first
  418 rows are materially identical; row 419 is censored and dropped. Existing
  documentation inconsistently states 419/90 and 418/89.

### 2.2 Model and preprocessing

- Deployed pipeline: `IterativeImputer -> StandardScaler -> LogisticRegression`.
- Logistic Regression: `C=1.0`, `class_weight="balanced"`, `max_iter=2000`,
  `solver="lbfgs"`, `random_state=42`.
- Imputer: default `BayesianRidge`, `max_iter=10`, `random_state=42`,
  `add_indicator=False`, `initial_strategy="mean"`, `sample_posterior=False`.
- Imputation and scaling are fit inside each CV fold. This is correct and must
  remain true in every experiment.
- 17 features: `trt, age, sex, ascites, hepato, spiders, edema, bili, chol,
  albumin, copper, alk.phos, ast, trig, platelet, protime, stage`.
- API-required fields: `age, sex, edema, bili, albumin`. `protime` is optional.
  This is not the Mayo five.
- `models/model.pkl` is byte-identical to `models/candidates/lr_model.pkl`,
  SHA-256 `BC96BB1D7399391EA103C65515A76E5F40E8A7CFD4ACDCE27D59D935020C31F1`,
  size 267713 bytes, 17 input features, classes `[0, 1]`.
- The deployed `/health` endpoint reported `model_version: bc96bb1d`, matching
  the local model hash prefix.

### 2.3 Missingness

| Feature | Missing rate |
|---|---:|
| `trig` | 30.7% |
| `chol` | 30.4% |
| `copper` | 22.5% |
| `trt` | 21.9% |
| `hepato` | 21.9% |
| `alk.phos` | 21.9% |
| `ast` | 21.9% |
| `spiders` | 21.9% |
| `ascites` | 21.9% |
| `platelet` | 3.3% |
| `stage` | 1.8% |
| `protime` | 0.6% |
| `age`, `bili`, `edema`, `sex`, `albumin` | 0% |

Missingness is structural, not random: 72 non-randomized patients share
missing `trt/ascites/hepato/spiders/alk.phos/ast`; a subset also lacks
`chol/copper/trig`. The 329 labeled cohort is 257 randomized plus 72
non-randomized patients. The imputer is therefore partly learning cohort
membership.

### 2.4 Reproduced out-of-fold metrics

Same 5-fold stratified split, seed 42, pipeline refit per fold:

| Feature set | Weighting | AUC | Brier | Calibration slope | Calibration intercept | Mean predicted | Observed |
|---|---|---:|---:|---:|---:|---:|---:|
| F17 | balanced | 0.8828 | 0.1364 | 0.725 | -0.472 | 0.460 | 0.401 |
| F17 | none | 0.8823 | 0.1338 | 0.735 | -0.180 | 0.413 | 0.401 |
| F5 | balanced | 0.8697 | 0.1449 | 0.919 | -0.426 | 0.463 | 0.401 |
| F5 | none | 0.8671 | 0.1438 | 0.936 | -0.063 | 0.405 | 0.401 |
| F6 | balanced | 0.8712 | 0.1436 | 0.921 | -0.437 | 0.464 | 0.401 |
| F17+IND | balanced | 0.8750 | 0.1424 | not yet computed | not yet computed | not yet computed | 0.401 |
| F16 | balanced | 0.8834 | 0.1364 | not yet computed | not yet computed | not yet computed | 0.401 |

Interpretation at freeze time: the 17-feature model has only a small
discrimination advantage over F5, while F5 has materially better calibration.
The `F17+IND` and `F16` rows are preliminary and must be recomputed by the
frozen harness before being treated as final.

### 2.5 Standardized coefficients

`bili +1.1727`, `stage +0.6830`, `copper +0.6353`, `albumin -0.5090`,
`edema +0.4197`, `age +0.4150`, `alk.phos -0.3799`, `ast +0.3541`,
`sex +0.2934`, `chol +0.2703`, `hepato +0.1942`, `spiders +0.1902`,
`ascites +0.1297`, `trt -0.0498`, `trig +0.0189`, `platelet +0.0147`,
`protime -0.0122`. Intercept `-0.05197`.

`protime` is effectively unused. `alk.phos` has a counterintuitive negative
coefficient. `chol` and `copper` are positive. These signs are consistent with
multicollinearity and overfitting and must be tested for stability.

### 2.6 Imputation sensitivity for Patient B

Documented Patient B inputs: age 55, female, edema 0, bilirubin 1.0 mg/dL,
albumin 3.5 g/dL, all optional fields blank. Current prediction: `27.4847%`.

| Scenario | Prediction |
|---|---:|
| Only five observed inputs, 12 imputed | 27.4847% |
| `protime = 10.8` added | 27.5358% |
| Cohort-typical optional values | 27.61% |
| Clinically normal optional values | 1.94% |
| All optional values at p10 | 4.91% |
| All optional values at p90 | 82.74% |
| `stage = 3` | 26.31% |
| `age = 60` | 31.44% |
| `albumin = 3.4` | 30.59% |

For this patient the imputer fills approximately `stage 3.07`, `copper 94.7`,
`alk.phos 2050`, `chol 346`. The resulting prediction is highly sensitive to
unmeasured features. The 5-feature model predicts 23.4-29.9% for the same
inputs, so imputation is not the sole reason the current output differs from
Mayo's 5.76%.

### 2.7 Artifact and documentation integrity

- `src/hepatiq/validation/calibration_plot.py:11-13` hardcodes `prob_true` and
  `prob_pred`; the plot is not computed from model predictions. This is a P0
  integrity issue. It is not modified by this protocol.
- `models/candidates/training_metrics.json` reports CV means (LR AUC 0.8800);
  `src/hepatiq/validation/report.md` reports OOF results (AUC 0.8828). This is
  a methodological difference, not necessarily stale data, and must be
  explained rather than silently reconciled.
- `README.md:7-12` and `AUTHORS.md:3-7` describe v2 survival and landmark
  models that are not present in this codebase.
- `README.md:40` and `docs/DEMO.md:41-43` describe the output as strongly or
  fully calibrated; the measured calibration slope is 0.725.
- `pyproject.toml` version is `2.0.0`; `src/hepatiq/__init__.py` is `0.1.0`.
- Local SQLite prediction history is empty, so the `25.00%` run cannot be
  recovered locally.

## 3. Research questions and hypotheses

### Primary questions

1. Does F17 provide a meaningful discrimination gain over F5 on the same
   cohort, endpoint and folds?
2. Is F5 better calibrated than F17?
3. How much do imputed optional features change predictions and risk bands for
   patients with only the five core inputs?

### Primary hypotheses

- **H1:** F17 does not meaningfully improve discrimination over F5. The
  pre-specified meaningful difference is `Delta AUC = 0.02`.
- **H2:** F5 is better calibrated than F17: calibration slope closer to 1 and
  smaller absolute calibration-in-the-large.
- **H3:** Imputation of the 12 optional features materially changes predictions
  and risk bands for patients with only the five core inputs.

### Secondary hypotheses

- H4: F16 (drop `trt`) performs similarly to F17.
- H5: F17+IND does not materially improve calibration or discrimination over
  F17.
- H6: Unweighted LR is better calibrated than weighted LR.
- H7: The `25.00%` versus `27.48%` discrepancy is reproducible from a specific
  payload and version; if not, it remains unexplained and is not treated as
  evidence about model quality.
- H8: The Mayo `5.76%` is not a valid probability comparator without its exact
  baseline survival, units and endpoint.

## 4. Data and endpoint

- Use `data/external/pbc.csv` read-only.
- Build the target with the existing definition: death or transplant within
  1825 days; drop censored before 1825 days.
- Confirm 329 labeled patients, 132 events, and identical labels to
  `data/processed/pbc_5yr_target.csv` before running models.
- Never read `data/interim/pbc_imputed.csv` or
  `data/interim/pbc_imputed_scaled.csv` in any CV or bootstrap path. They are
  full-cohort transformations and would leak.
- Do not modify raw, processed or external data.

## 5. Feature sets

| ID | Features | Role |
|---|---|---|
| F5 | `age, bili, albumin, protime, edema` | Mayo-compatible primary comparator |
| F6 | F5 + `sex` | App-required comparator |
| F16 | F17 minus `trt` | Structural-missingness sensitivity |
| F17 | Current 17 features | Deployed model |
| F17+IND | F17 plus missingness indicators | Secondary missingness model |

`F17+IND` uses one indicator per feature with any missingness, computed inside
the training fold. It is secondary because missing indicators can help under
some missingness mechanisms and harm under outcome-dependent missingness.

## 6. Models

### Primary

- Logistic Regression, L2, `C=1.0`, `solver="lbfgs"`, `max_iter=2000`,
  `random_state=42`.
- Two weighting regimes: `class_weight="balanced"` and `class_weight=None`.
- No hyperparameter tuning in the primary analysis.

### Secondary exploratory

- Random Forest: existing hyperparameters (`n_estimators=300`, `max_depth=4`,
  `min_samples_leaf=8`, `max_features="sqrt"`, `class_weight="balanced"`).
- XGBoost: existing hyperparameters (`n_estimators=150`, `max_depth=3`,
  `learning_rate=0.05`, `subsample=0.8`, `colsample_bytree=0.8`,
  `reg_lambda=2.0`, `reg_alpha=0.5`, `min_child_weight=5`,
  `scale_pos_weight` computed from the training fold).
- Secondary models use the same folds and metrics. They are descriptive only
  and cannot be selected for deployment from this audit.

## 7. Validation design

### 7.1 Primary out-of-fold analysis

- One pre-specified stratified 5-fold split, seed 42, matching the current
  validation report.
- Same folds for every feature set and model.
- Pipeline fit only on the training part of each fold.
- Save fold assignments and OOF predictions.

### 7.2 Stability analysis

- 10 repeated stratified 5-fold splits, seeds 42-51.
- Same folds across feature sets within each repeat.
- Report mean, SD, minimum and maximum across repeats. Do not treat folds as
  independent observations.

### 7.3 Optimism correction

- 500 stratified bootstrap resamples per feature set.
- Repeat all modeling steps inside each bootstrap: imputation, scaling,
  missing-indicator construction and fitting.
- Report apparent, optimism and optimism-corrected AUC, Brier and calibration
  slope/intercept.
- If runtime is prohibitive, reduce to 200 resamples and record the deviation;
  do not silently reduce.

### 7.4 Held-out 312/106 split

- Use exactly once, after this protocol is frozen.
- Derivation: 312 randomized patients; held-out: 106 non-randomized patients.
- The held-out set has 72 labeled patients and 34 events; 70 have a complete
  Mayo score (33 events).
- No model selection, no threshold tuning, no recalibration fitting.
- Report discrimination and Brier as supportive. Do not present calibration
  slope from a model fitted on held-out labels.
- Label it an internal cohort split, not external validation.

### 7.5 Leakage controls

- A test asserts that the research loader never reads `data/interim`.
- A test asserts that the imputer/scaler are fit only on training folds in the
  harness.
- A test asserts that `time`, `status` and `id` are absent from feature frames.
- A test asserts deterministic fold assignment for a fixed seed.

## 8. Calibration analysis (co-primary)

For each feature set and weighting regime:

- Brier score with patient-level bootstrap CI.
- Calibration slope and intercept from OOF logits.
- Calibration-in-the-large.
- ECE with 10 equal-frequency bins and ICI; report both.
- Reliability curve from genuine OOF predictions with a loess smoother.
- Decision curve/net benefit across thresholds 0.05-0.60, labelled exploratory.
- Precision, recall, sensitivity, specificity, PPV, NPV and F1 at thresholds
  0.15, 0.40 and 0.50. No threshold tuning.
- Risk-band reclassification: proportion moving between `<0.15`,
  `0.15-0.40` and `>0.40`.

Bootstrap CIs: 2000 patient-level resamples for single-model metrics; paired
bootstrap for differences between models.

For multiple imputation, use a "pool last" approach: compute metrics per
imputation, then pool with Rubin's rules where valid. For calibration curves,
report per-imputation curves or overlay them. Do not pool predictions before
evaluating calibration.

## 9. Feature ablation comparison

- Primary contrast: F17 versus F5.
- Report paired `Delta AUC` and `Delta Brier` with patient-level bootstrap CIs.
- F5 is nested in F17, so do not rely on DeLong:
  - Primary: paired bootstrap and bootstrap optimism-corrected `Delta AUC`.
  - Secondary: likelihood-ratio or Wald test for the added predictors.
  - DeLong only as a caveated secondary analysis.
- Report coefficient stability across repeats and bootstrap resamples: mean,
  SD, sign consistency, VIF and condition number.
- Report learning curves for F5 and F17.
- Secondary RF/XGB comparisons are descriptive only.

## 10. Imputation sensitivity

### 10.1 Patient B investigation

- Reproduce Patient B exactly and record the payload.
- Tornado across all 12 optional features using:
  - clinically normal values;
  - cohort-typical values;
  - cohort p10, p50 and p90;
  - observed conditional distributions.
- Report the imputed values used by the pipeline for each scenario.
- Report prediction range, IQR and risk-band changes.
- Diagnose why the prediction is sensitive: imputed values, coefficient
  magnitudes, feature correlations, extrapolation and comparison with F5.

### 10.2 All-patient sensitivity

For every patient with only the five core inputs:

- Plug-in conditional-mean imputation (current behavior).
- 20 multiple imputations with `IterativeImputer(sample_posterior=True)`.
- Scenario grid: clinically normal, cohort-typical, p10 and p90.
- Randomized versus non-randomized missingness patterns.

Report prediction distribution, proportion changing risk band, and changes in
SHAP attributions. Label imputed values as synthetic. Do not present them as
measurements.

### 10.3 Missing indicators

F17+IND is secondary. Report whether indicators improve discrimination or
calibration and whether they change the imputation-sensitivity conclusion.
Do not assume missing indicators are beneficial.

## 11. Censoring sensitivity

- Best-case/worst-case bounds for the 89 patients censored before five years.
- Composite endpoint (primary) versus death-only (sensitivity).
- IPCW as an exploratory analysis; report instability if the censoring model
  is weak.
- No survival model in this protocol. Cox/RSF/competing risks remain a separate
  future protocol.

## 12. Mayo comparability

- Treat Mayo `5.76%` as non-comparable until its exact formula, baseline
  survival, units and endpoint are verified.
- The repository's `mayo_risk_score.py` computes the score `R`, not a
  probability.
- Compare discrimination only on common patients.
- Do not calibrate HepatiQ to Mayo.
- Do not fit anything on the 312/106 split.
- If the exact calculator is later pinned, add a separate addendum before
  running any probability comparison.

## 13. `25.00%` versus `27.48%` verification

Create `docs/research/REPRODUCTION_25_VS_27.md` with:

- exact JSON payload and units;
- optional fields left blank;
- app URL, version/commit and timestamp;
- `/health` response including `model_version`;
- local model SHA-256;
- direct pipeline prediction, local API prediction and deployed API
  prediction;
- the difference and likely cause.

Current verified baseline: local commit `db2bf51`, model SHA-256
`BC96BB1D...C31F1`, deployed model version `bc96bb1d`, Patient B default
`27.4847%`. The local history table is empty. If the exact `25.00%` payload
cannot be supplied, the document records `25.00% unreproduced` and does not
treat the difference as evidence.

## 14. Multiplicity and decision rules

### Primary endpoints

1. `Delta AUC` F17 versus F5.
2. `Delta calibration slope` F17 versus F5.
3. Imputation prediction range for patients with five observed inputs.

Use Holm correction for the three primary tests. All other analyses are
secondary or exploratory.

### Decision rules

- **Added discrimination supported** only if the `Delta AUC` 95% CI excludes 0
  and the lower bound exceeds 0.02.
- **Better calibration** if F5's slope is closer to 1 and `|CITL|` is smaller,
  with consistent direction across repeats.
- **Material imputation instability** if the plausible prediction range exceeds
  10 percentage points or a meaningful proportion of patients change risk band.
- **Overfitting signal** if calibration slope is below 0.8, multiple VIFs exceed
  5, or coefficient signs are unstable.
- **No equivalence claims.** A non-significant difference is inconclusive.
- **No clinical validation claims.**

## 15. Integrity issue: hardcoded calibration plot

- Record as a P0 critical integrity issue.
- Do not modify `src/hepatiq/validation/calibration_plot.py` in this research
  branch.
- Prepare a separate proposal at
  `docs/research/proposals/CALIBRATION_PLOT_CORRECTION.md`.
- The proposal must specify:
  - why the hardcoded arrays are invalid;
  - how to compute a genuine OOF reliability curve;
  - required tests;
  - expected behavior when OOF predictions are unavailable.
- After separate review and approval, implement on a separate branch:
  `fix/calibration-plot-integrity`.
- Do not mix that change with the ablation experiments.

## 16. Files and boundaries

### New research files

- `src/hepatiq/research/__init__.py`
- `src/hepatiq/research/config.py`
- `src/hepatiq/research/data.py`
- `src/hepatiq/research/metrics.py`
- `src/hepatiq/research/ablation.py`
- `src/hepatiq/research/imputation.py`
- `src/hepatiq/research/censoring.py`
- `src/hepatiq/research/mayo.py`
- `src/hepatiq/research/reporting.py`
- `scripts/research/run_audit.py`
- `tests/test_research_config.py`
- `tests/test_research_metrics.py`
- `tests/test_research_leakage.py`
- `tests/test_research_imputation.py`
- `docs/research/artifacts/` for summary tables and genuine OOF curves

### Explicitly untouched

- `models/model.pkl`
- `models/candidates/*`
- `src/hepatiq/backend/main.py`
- `src/hepatiq/risk_bands.py`
- `src/hepatiq/ml/train.py`
- `src/hepatiq/ml/impute_pipeline.py`
- `src/hepatiq/validation/calibration_plot.py` until the separate integrity
  branch
- `data/raw/*`, `data/processed/*`, `data/external/*`

## 17. Execution gates

| Gate | Action | Stop condition |
|---|---|---|
| 1 | Create branch, write protocol, freeze with protocol-only commit | No production edits |
| 2 | Implement harness and tests; smoke-test | Tests pass; no production diff |
| 3 | Run primary OOF, repeated CV and calibration | Results reproducible |
| 4 | Run imputation, censoring, Mayo and reproduction analyses | Frozen protocol honored |
| 5 | Run 312/106 once, after freeze | No selection or calibration fitting |
| 6 | Write audit report and calibration-plot correction proposal | Review before production fix |
| 7 | Separate integrity-fix branch and documentation corrections | Explicit approval before merge/deploy |

## 18. Changelog and deviations

- **2026-11-02, pre-analysis correction:** clarified the held-out counts. The
  106-patient validation split contains 72 labeled patients with 34 events;
  70 of those patients have a complete Mayo score, and those 70 contain 33
  events. The held-out split had not been evaluated when this correction was
  made. This is a factual clarification, not an analysis change.
- **2026-11-02, exploratory-value correction:** regenerated the Patient B
  optional-value scenarios with the leak-free harness. The earlier table used
  a different scenario definition. The corrected values are 27.61%
  (cohort-typical), 1.94% (clinically normal), 4.91% (p10) and 82.74% (p90).
  Only the 12 genuinely imputed fields are varied; the five observed fields
  stay fixed. The frozen hypotheses and analysis plan are unchanged.

No other deviations yet. Any post-freeze change must be appended here with a
date, reason and whether it is exploratory.
