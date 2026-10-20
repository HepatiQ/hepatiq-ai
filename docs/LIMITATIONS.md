# Limitations

HepatiQ is an academic research prototype. This document states what the model and the
software *cannot* support, so results are never read as more than the evidence allows.
Numbers cited here come from `validation/report.md` and `models/training_metrics.json`.

## Cohort and data

- **Single historical cohort.** Everything is trained and evaluated on the Mayo Clinic PBC
  dataset (1974–1984). Treatment standards, assay methods, and patient populations have
  changed since; performance elsewhere is unproven.
- **Small sample.** 419 initial records, 329 after the 5-year outcome filter (90 patients
  censored before 5 years were excluded). With 132 events, every confidence interval is
  wide — out-of-fold ROC-AUC is **0.8828 [0.8409, 0.9185]**, and intervals this wide mean
  the true value on new patients could plausibly sit anywhere in that band.
- **Censoring handled by exclusion, not modeling.** Dropping patients censored before
  5 years removes exactly those whose outcomes are unknown; if censoring relates to
  prognosis (sicker patients lost to follow-up), the training distribution is biased.
  A time-to-event model (Cox, survival forests) would handle this properly.
- **PBC-specific.** Primary biliary cholangitis is one autoimmune condition. The model is
  not a general liver-disease or cirrhosis risk score — the inputs, the learned weights,
  and the validation all assume PBC.

## Missing clinical benchmark

- A comparison against **MELD is not possible from this data**: MELD requires bilirubin,
  INR, and creatinine, and the dataset has no INR or creatinine columns. Rather than
  fabricate a "MELD" from prothrombin time and an invented creatinine, validation uses a
  class-prior baseline (ROC-AUC ≈ 0.5 by construction). The model clearly beats it
  (0.8828 vs 0.4924), but "beats naive guessing" is a much weaker claim than
  "beats the established clinical standard."
- Mayo Risk Score, GLOBE, and UK-PBC comparisons remain future work and require either
  those datasets or the missing labs.

## Model and predictions

- **Associations, not causation.** SHAP values explain what the *model* used; they are
  not treatment targets. "Bilirubin raises the score" describes the fitted function, not
  an intervention effect.
- **Imputed inputs produce imputed explanations.** When optional fields are left blank,
  `IterativeImputer` fills them before prediction; their SHAP values describe modeled
  values, not measurements. The UI marks these with `*`, but their apparent certainty is
  synthetic.
- **Additive model.** Logistic Regression is linear in the transformed features — it
  cannot represent interactions (e.g. bilirubin × stage) unless the data happens to
  support them additively. Calibration is reported (Brier 0.1364 OOF) but no reliability
  diagram yet, so miscalibration in risk tails is unquantified.
- **Composite endpoint.** The target is death *or* liver transplant within 5 years;
  the two have different clinical meanings and are pooled here.

## Software and deployment

- **No authentication or authorization.** The API and UI are open to anyone who can reach
  the port: no login, no TLS, no rate limiting. Acceptable for a local demo, not for
  any deployment handling real patient data (which would also need PHI controls,
  encryption at rest, and audit logging the project does not implement).
- **Local-only history.** Predictions are logged to a gitignored SQLite file on the
  machine running the server; there is no backup, retention policy, or tamper protection.
- **No monitoring.** Nothing tracks prediction drift, input-range violations in
  production, or model degradation over time; the model is a frozen `.pkl` from one
  training run.
- **Research prototype status.** Not FDA-approved, CDSCO-approved, or clinically
  validated; not a substitute for physician judgment (see the README disclaimer).

## What the evidence does support

On this cohort, with this pipeline (leakage-controlled 5-fold CV, seed 42), the deployed
Logistic Regression discriminates 5-year severe events substantially better than a
constant baseline, with calibration better than the baseline, and the API's numerical
output is exactly reproducible against direct `joblib` inference (asserted in the test
suite). That is the claim; nothing beyond it is.
