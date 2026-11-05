# Results: Feature Ablation and Imputation Audit

Status: **draft. Primary, robustness, one-time internal held-out, sensitivity,
and SHAP attribution analyses are complete. Two items remain blocked: exact
reproduction of the 25.00% Patient B payload and the Mayo 5.76% probability
comparison.** No production model, inference path, threshold, or deployment was
changed. The held-out split has been used once and is now sealed by a guard in
the CLI.

Protocol: [FEATURE_ABLATION_IMPUTATION_AUDIT.md](FEATURE_ABLATION_IMPUTATION_AUDIT.md)
frozen in `1e10a13` and corrected in `a691da3`; hash in
[PROTOCOL.sha256](PROTOCOL.sha256).

## Provenance

| Item | Value |
|---|---|
| Branch | `research/feature-ablation-imputation-audit` |
| Base | `main` at `db2bf514c37f27bfbae13ab79b559350bdcee970` |
| Model | `models/model.pkl`, SHA-256 `BC96BB1D7399391EA103C65515A76E5F40E8A7CFD4ACDCE27D59D935020C31F1` |
| Model version | `bc96bb1d` (`/health`) |
| Pipeline | `IterativeImputer(max_iter=10, random_state=42)` -> `StandardScaler` -> `LogisticRegression(C=1.0, class_weight="balanced", solver="lbfgs", max_iter=2000, random_state=42)` |
| Cohort | 329 labeled patients, 132 events, 89 censored/dropped |
| Validation | 128 passed, 2 skipped with E2E backend disabled (Linux CI); 37 research tests passed; `ruff check .` passed. Windows fresh worktrees can fail external-data SHA checks because of CRLF checkout, which is not a code failure. |
| Artifacts | [`artifacts/`](artifacts/) |

F17 means the deployed 17 features. F5 is the Mayo-compatible subset
`age, bili, albumin, protime, edema`. F16 drops `trt`. F17+IND adds missingness
indicators. Ordinary models are unweighted; "weighted" means
`class_weight="balanced"`. Primary seed is 42.

## Cohort and target

| Quantity | Value |
|---|---:|
| Raw patients | 418 |
| Randomized | 312 |
| Non-randomized | 106 |
| Labeled at 5 years | 329 |
| Events (death or transplant) | 132 |
| Censored/dropped | 89 |
| Deaths only | 115 |
| Transplants | 17 |
| Event rate, labeled (132/329) | 40.12% |

Target: death or transplant within 1825 days = 1; known event-free at 1825 = 0;
censored before 1825 is dropped. This is a composite endpoint, not
transplant-free survival.

## Primary out-of-fold results

Seed 42, 5-fold stratified cross-validation, preprocessing fitted within each
fold.

| Model | Weighting | AUC (95% CI) | Brier | Slope | CITL | ECE | ICI |
|---|---|---:|---:|---:|---:|---:|---:|
| F17 | unweighted | 0.8823 | 0.1338 | 0.735 | -0.101 | 0.036 | 0.250 |
| F17 | weighted | 0.8828 (0.8424, 0.9180) | 0.1364 | 0.725 | -0.498 | 0.062 | 0.248 |
| F5 | unweighted | 0.8671 | 0.1438 | 0.936 | -0.026 | 0.068 | 0.255 |
| F5 | weighted | 0.8697 (0.8245, 0.9087) | 0.1449 | 0.919 | -0.410 | 0.083 | 0.255 |

All unweighted slopes are below 1; the weighted models overpredict more
strongly. F17 has lower ECE but a worse calibration slope than F5. ICI is
similar. ECE alone is not sufficient evidence of better calibration.

## F17 versus F5

Paired bootstrap, 2000 resamples, seed 42. Deltas are F17 minus F5, so
direction is metric-dependent. Higher AUC is better, so a positive AUC delta
favors F17. Lower Brier is better, so a negative Brier delta favors F17.
Calibration slope is better when closer to 1; all slopes here are below 1, so
a positive slope delta would favor F17 and the negative slope deltas favor F5.

| Metric | Weighting | Delta | 95% CI | p |
|---|---|---:|---:|---:|
| AUC | weighted | +0.0132 | -0.0159, +0.0434 | 0.367 |
| Brier | weighted | -0.0084 | -0.0252, +0.0094 | 0.330 |
| Slope | weighted | -0.1938 | -0.4665, +0.0091 | 0.062 |
| AUC | unweighted | +0.0152 | -0.0136, +0.0449 | 0.288 |
| Brier | unweighted | -0.0100 | -0.0269, +0.0083 | 0.257 |
| Slope | unweighted | -0.2006 | -0.4706, -0.0036 | 0.048 |

Holm correction over AUC and slope: weighted 0.124 and 0.734; unweighted
0.096 and 0.576. No primary contrast survives multiplicity correction.
Protocol deviation: the third protocol primary endpoint is a descriptive
imputation range, not a hypothesis test, so Holm was applied to the two
testable contrasts rather than to all three endpoints.

The AUC gain is consistently positive but below the pre-specified 0.02
materiality threshold and its confidence interval includes zero. F17 does not
demonstrate materially better discrimination. F5 has the better calibration
slope; the weighted slope difference is borderline and the unweighted result
does not survive Holm correction.

## Repeated split stability

Seeds 42-51.

| Model | Weighting | AUC mean (sd) | Brier mean (sd) | Slope mean (sd) |
|---|---|---:|---:|---:|
| F17 | unweighted | 0.8822 (0.0038) | 0.1351 (0.0024) | 0.764 (0.032) |
| F17 | weighted | 0.8833 (0.0039) | 0.1362 (0.0025) | 0.753 (0.032) |
| F5 | unweighted | 0.8662 (0.0040) | 0.1428 (0.0020) | 0.943 (0.039) |
| F5 | weighted | 0.8678 (0.0040) | 0.1440 (0.0019) | 0.919 (0.040) |

F17-F5 AUC delta across seeds: weighted +0.01546 (sd 0.00501), 10/10 positive;
unweighted +0.01603 (sd 0.00501), 10/10 positive. Slope delta: weighted
-0.1653 (sd 0.0498), 10/10 negative; unweighted -0.1794 (sd 0.0499), 10/10
negative.

The direction is stable; the magnitude is small. The calibration tradeoff is
also stable.

## Optimism correction

500 stratified bootstrap resamples, seed 42. Apparent values are in-sample;
corrected values subtract mean bootstrap optimism.

| Model | Weighting | AUC apparent | AUC optimism | AUC corrected | Brier apparent | Brier corrected | Slope apparent | Slope corrected |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| F17 | unweighted | 0.9136 | 0.0249 | 0.8887 | 0.1152 | 0.1339 | 1.042 | 0.800 |
| F17 | weighted | 0.9151 | 0.0251 | 0.8901 | 0.1167 | 0.1353 | 1.022 | 0.783 |
| F5 | unweighted | 0.8773 | 0.0079 | 0.8694 | 0.1365 | 0.1422 | 1.065 | 0.981 |
| F5 | weighted | 0.8795 | 0.0082 | 0.8713 | 0.1377 | 0.1434 | 1.035 | 0.954 |

F17 carries roughly three times the AUC optimism of F5. Corrected F17-F5
delta: unweighted +0.0193, weighted +0.0188, still just below the 0.02
materiality threshold. Corrected slope gap: unweighted -0.181, weighted
-0.171. The robustness conclusion is unchanged and slightly stronger:
F17's apparent discrimination gain is partly optimism, and its calibration
slope is worse after correction. The optimism-corrected deltas are point
estimates without a paired bootstrap confidence interval; they do not satisfy
the protocol's lower-bound materiality rule and are reported as a sensitivity
analysis, not as confirmation.

## Secondary feature sets

| Model | Weighting | AUC | Brier | Slope | CITL | ECE |
|---|---|---:|---:|---:|---:|---:|
| F6 | unweighted | 0.8695 | 0.1416 | 0.936 | -0.040 | 0.062 |
| F6 | weighted | 0.8712 | 0.1436 | 0.921 | -0.424 | 0.063 |
| F16 | unweighted | 0.8818 | 0.1338 | 0.740 | -0.109 | 0.039 |
| F16 | weighted | 0.8834 | 0.1364 | 0.732 | -0.507 | 0.063 |
| F17+IND | unweighted | 0.8735 | 0.1401 | 0.682 | -0.120 | 0.047 |
| F17+IND | weighted | 0.8750 | 0.1424 | 0.676 | -0.514 | 0.073 |

F16 is the best point estimate for AUC and essentially tied with F17 on
calibration. `trt` is not adding value. Missingness indicators do not help;
F17+IND is worse than F17 on both AUC and calibration.

## Imputation sensitivity, Patient B

Patient B is a 55-year-old woman with edema 0, total bilirubin 1.0 mg/dL, and
albumin 3.5 g/dL. Five fields are observed: age 55, sex (female), edema 0,
bilirubin 1.0, and albumin 3.5. The other 12 fields are blank and imputed.

The percentile scenarios (p10/p50/p90) vary the 12 imputed optional fields
together. The single-field `age`, `albumin`, and `bili` rows are observed-field
stress tests that perturb observed values; `protime` and `stage` are single
optional-field scenarios.

Deployed F17 model 5-year prediction: **27.4847%**. This is a 5-year composite
outcome probability, not a transplant-free survival percentage.

| Scenario | F17 | F5 fitted on the full cohort |
|---|---:|---:|
| Only observed values | 27.4847% | 29.78% |
| Cohort-typical optional values | 27.61% | 29.71% |
| Clinically normal optional values | 1.94% | 29.61% |
| All optional values at p10 | 4.91% | 28.90% |
| All optional values at p50 | 27.61% | 29.71% |
| All optional values at p90 | 82.74% | 31.26% |
| `protime = 10.8` | 27.54% | 29.91% |
| `stage = 3` | 26.31% | not applicable |
| `age = 60` | 31.44% | 33.22% |
| `albumin = 3.4` | 30.59% | 33.05% |
| `bili = 1.1` | 28.12% | 30.65% |

F17 optional-value range: **80.80 percentage points**. F5 optional-value
range: **2.36 percentage points**. F5's all-scenario range, including the
observed-field stress tests, is **4.32 percentage points**.

Twenty-draw multiple imputation:

| Model | Mean | Range | Range (pp) | Risk bands (low/moderate/high) |
|---|---:|---:|---:|---:|
| F17 | 27.83% | 3.62-63.73% | 60.10 | 6 / 9 / 5 |
| F5 | 29.24% | 27.57-31.67% | 4.10 | 0 / 20 / 0 |

The F17 prediction is dominated by which plausible values are imputed. The F5
prediction is comparatively stable. This is a material robustness problem for
F17 and supports the imputation-sensitivity hypothesis. The F5 comparison is
exploratory: the F5 model was fitted on the full cohort for this illustration,
not deployed.

Interpretation: at Patient B's fixed observed values, F17's optional inputs
control the risk band. The point estimate of 27.4847% is not a robust
individual-level estimate.

## All-patient imputation sensitivity

Every labeled patient was reduced to the five observed fields (age, sex,
bilirubin, albumin, edema); the other 12 fields were imputed. Scenario values
were applied globally to all patients. Multiple imputation used 20 posterior
draws.

| Quantity | Value |
|---|---:|
| Patients | 329 |
| Baseline risk bands (low/moderate/high) | 57 / 129 / 143 |
| MI-mean risk bands (low/moderate/high) | 25 / 148 / 156 |
| Mean per-patient scenario range | 73.65 pp |
| Maximum per-patient scenario range | 87.92 pp |
| Mean per-patient MI SD | 18.53 pp |
| Mean band-change rate, baseline to MI mean | 17.33% of patients |
| Any-draw band change | 85.11% |

| Scenario | Mean prediction | Mean delta vs plug-in |
|---|---:|---:|
| Only observed, plug-in | 43.34% | 0.00 pp |
| Cohort-typical optional | 41.62% | -1.72 pp |
| Clinically normal optional | 10.34% | -33.00 pp |
| Optional p10 | 16.56% | -26.77 pp |
| Optional p90 | 83.99% | +40.65 pp |
| 20-draw MI mean | 44.78% | - |

Randomized versus non-randomized:

| Group | n | Mean scenario range | Mean MI SD | Mean band-change rate | Any-draw change |
|---|---:|---:|---:|---:|---:|
| Randomized | 257 | 72.64 pp | 18.32 pp | 15.18% of patients | 85.99% |
| Non-randomized | 72 | 77.22 pp | 19.27 pp | 25.00% of patients | 81.94% |

The instability is not confined to Patient B. Optional-value scenarios move
the average patient by roughly 74 percentage points, and 85% of patients have
at least one posterior draw that changes their risk band. Non-randomized
patients, whose missingness is structural, change bands more often on average.
The plug-in prediction is not a stable individual-level quantity for the
17-feature model.

## SHAP attribution changes under imputation

SHAP values are local linear log-odds contributions relative to a 100-patient
background sample (seed 42). They explain the fitted model; they are not
causal effects. Imputed inputs are synthetic and are not measurements.

Patient B:

| Scenario | Prediction | Top feature (impact, log-odds) | Mean absolute SHAP change |
|---|---:|---|---:|
| Only observed, plug-in | 27.4847% | bilirubin (-0.640) | 0.000 |
| Cohort-typical optional | 27.61% | bilirubin (-0.640) | 0.051 |
| Clinically normal optional | 1.94% | stage (-1.593) | 0.223 |
| Optional p10 | 4.91% | stage (-0.821) | 0.155 |
| Optional p90 | 82.74% | copper (+0.874) | 0.229 |
| Protime 10.8 | 27.54% | bilirubin (-0.640) | 0.0003 |

The clinically normal and percentile scenarios do not merely scale the same
explanation: the leading contributor moves from bilirubin to stage or copper.
That is a change in the explanation, not just a change in the score.

All patients:

| Scenario | Mean absolute SHAP change | Largest changing feature | Patients whose top feature changes |
|---|---:|---|---:|
| Cohort-typical optional | 0.068 | copper | 1.5% |
| Clinically normal optional | 0.237 | stage | 90.0% |
| Optional p10 | 0.169 | stage | 66.9% |
| Optional p90 | 0.219 | copper | 77.5% |
| 20-draw MI, per draw | 0.145 | copper | 52.9% |
| 20-draw MI, mean across draws | 0.032 | copper | 0.6% |

Under the baseline plug-in explanation, bilirubin is the top absolute
contributor for 185 of 329 patients, albumin for 53, age for 47, sex for 28,
and edema for 16. Clinically normal optional values move the top contributor
in 90% of patients, and individual posterior draws move it in 52.9%. Averaging
20 draws attenuates the mean attribution shift to 0.032 log-odds and a 0.6%
top-feature change rate, but that averaging is a reporting choice, not evidence
that any single draw is stable.

## Collinearity, coefficient stability, and learning curves

Condition number: 3.45. Maximum VIF: bilirubin 2.31; ascites 1.89; edema 1.82;
stage 1.60; hepatomegaly 1.55. All VIF values are below 2.31. Multicollinearity
does not explain the instability.

Across 50 refits, bilirubin, albumin, copper, alkaline phosphatase, AST, stage,
age, sex, and edema keep consistent signs. Protime, triglycerides, platelets,
and `trt` do not. Those low-signal coefficients should not be interpreted
individually.

Learning curves:

| Model | Train AUC at max n | Test AUC at max n |
|---|---:|---:|
| F17 | 0.918 | 0.880 |
| F5 | 0.880 | 0.865 |

F17 has the larger train-test gap. This is consistent with the small,
unstable incremental signal and with the optimism-corrected result.

## Censoring sensitivity

| Scenario | Denominator (n) | Events | Event rate |
|---|---:|---:|---:|
| Primary (censor before 1825 dropped) | 329 labeled | 132 | 40.12% (132/329) |
| Best case (all censored survive) | 418 all-cohort | 132 | 31.58% (132/418) |
| Worst case (all censored have events) | 418 all-cohort | 221 | 52.87% (221/418) |
| Death only, transplant treated as non-event | 312 labeled | 115 | 36.86% (115/312) |

The primary labeled-cohort event rate is 40.12% (132/329). Under the
all-cohort best/worst-case bounds (n=418) it spans 31.58% to 52.87%
(132/418 to 221/418). The death-only analysis drops 106 records
(transplants and censored patients), so it answers a different question.
Results should be reported with the composite-endpoint definition, not as
transplant-free survival.

## Mayo comparison

HepatIQ predictions here are out-of-fold F17 weighted, seed 42. The Mayo Risk
Score is a linear score, so only discrimination is compared. Probability
comparison remains blocked because the Mayo baseline survival function is not
in the repository.

| Metric | Value |
|---|---:|
| Common patients | 327 |
| Events | 131 |
| Mayo AUC (95% CI) | 0.8864 (0.8458, 0.9219) |
| HepatIQ OOF AUC (95% CI) | 0.8817 (0.8421, 0.9184) |
| Delta (HepatIQ - Mayo) | -0.0047 (-0.0345, +0.0255) |
| p | 0.783 |

There is no evidence that HepatIQ discriminates better than the Mayo score on
this cohort; the confidence interval includes both a modest advantage and a
modest disadvantage. A null result is not evidence of equivalence. An earlier
resubstitution estimate of 0.914 for HepatIQ was optimistic because the
deployed model was scored on its own training cohort; it is not a valid
comparison and is discarded.

Mayo's 5.76% probability comparison remains blocked until the exact formula,
baseline survival function, units, and endpoint are verified.

## Held-out evaluation

One-time internal split: train on randomized patients, test on non-randomized
patients. This is an internal cohort split, not external validation. No model
selection, threshold tuning, or recalibration was performed. Per protocol,
only discrimination and Brier are interpreted; calibration slope is not used.

| Model | Train n / events | Test n / events | AUC (95% CI) | Brier (95% CI) |
|---|---:|---:|---:|---:|
| F17 | 257 / 98 | 72 / 34 | 0.8259 (0.7280, 0.9114) | 0.1761 (0.1256, 0.2289) |
| F5 | 257 / 98 | 72 / 34 | 0.8359 (0.7343, 0.9262) | 0.1647 (0.1184, 0.2147) |

F17's point estimates were lower than F5's on AUC (0.8259 vs 0.8359) and
worse on Brier (0.1761 vs 0.1647). This comparison is inconclusive in one
internal split: the test set is small (72 patients / 34 events), structural
missingness differs between the randomized training patients and the
non-randomized test patients, and no paired delta confidence interval was
reported. The result does not support a material 17-feature advantage, but it
also does not establish that F5 is better.

## Reproduction of 25.00% versus 27.4847%

The deployed model reproduces **27.4847%** for Patient B with the documented
payload. The exact payload that produced **25.00%** is not in the repository
and has not been supplied. The difference is not attributable to a known code
path.

The 25.00% value is therefore **unreproduced**, not refuted. It should not be
used in clinical or regulatory material until the original payload, units,
optional-field blanks, app version, and timestamp are recovered.

## Interpretation against the hypotheses

- H1 (small discrimination gain, calibration tradeoff): supported as a failure
  to demonstrate a material gain, not as proof of no difference. F17 gains
  0.013-0.015 AUC out-of-fold and 0.019 after optimism correction, below the
  0.02 materiality threshold, while its calibration slope is worse.
- H2 (F17 calibration is worse): partially supported. Slope is worse and
  weighted CITL is more negative; ECE favors F17 and ICI is similar. The
  out-of-fold slope result is borderline under Holm correction; the
  optimism-corrected slope gap is larger but has no confidence interval, so it
  is supporting evidence rather than a confirmed effect.
- H3 (imputation sensitivity): strongly supported. F17 optional-value range is
  80.8 percentage points for Patient B, 73.6 points on average across patients,
  and multiple imputation spans 60.1 points for Patient B. SHAP explanations
  are also unstable: clinically normal values change the top contributor in
  90% of patients, and individual MI draws change it in 52.9%.
- H4 (25.00% reproducibility): blocked. The exact payload is missing.
- H5 (held-out performance): evaluated once; inconclusive in one internal
  split. F5's point estimates were slightly better on held-out AUC and Brier,
  but the test set is small (72 patients / 34 events), train and test differ in
  structural missingness, and no paired delta CI was reported. This does not
  support a material 17-feature advantage and does not establish that F5 is
  better.

## What this means

F17 is a modest discrimination gain over F5, not a material one. Its
individual-level prediction is highly sensitive to plausible imputation of
optional inputs, and its calibration slope is worse. This is a cohort-wide
pattern, not a Patient B anomaly. F5 is less discriminative but markedly more
stable and has a better calibration slope and less negative CITL; ECE and ICI
do not consistently favor F5. The deployed 17-feature model
is not defensible as a precise individual-risk calculator on this evidence.

The one-time held-out check is inconclusive, not a demonstration that F5 is
better: F5's point estimates were slightly better on discrimination and Brier,
but the internal split is small (72 patients / 34 events), train and test
differ in structural missingness, and no paired delta CI was reported. This
does not prove the model is harmful, and it does not establish that F5 should
replace it in production. It does mean that claims of a large incremental
benefit from the 17 features, or of a stable Patient B risk, are not supported
by the audit.

## Pending

1. Mayo probability comparison, if the baseline survival function is supplied.
2. Exact 25.00% payload recovery.
3. Calibration plot correction; the current plot in this research branch still
   uses hardcoded arrays and is not evidence. The correction on
   `fix/calibration-plot-integrity` is not merged into this research branch.
4. External validation; the held-out split is internal.

## Artifact map

- `ablation.json`, `ablation_summary.csv`: all feature sets, primary and
  repeated metrics.
- `calibration_primary.json`: calibration curves, thresholds, decision curves.
- `primary_comparisons.json`: paired F17-F5 contrasts.
- `repeated_primary_deltas.json`: seeds 42-51.
- `diagnostics.json`, `coefficient_stability.csv`: collinearity and 50-refit
  stability.
- `collinearity.json`, `learning_curves.json`: exploratory diagnostics.
- `imputation_patient_b.json`, `imputation_scenarios.csv`,
  `imputation_tornado.csv`: Patient B sensitivity.
- `all_patient_sensitivity.json`: cohort-wide imputation sensitivity.
- `imputation_attribution.json`: Patient B and cohort-wide SHAP changes.
- `optimism.json`: 500-resample optimism correction for F5 and F17.
- `patient_b_f5_vs_f17.json`: F5 exploratory comparison.
- `censoring_bounds.json`: censoring sensitivity.
- `mayo_discrimination.json`: OOF discrimination-only comparison.
- `heldout_once.json`: sealed one-time internal split result.
