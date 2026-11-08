# Limitations

HepatiQ is an academic research prototype. This document states what the model and the
software *cannot* support, so results are never read as more than the evidence allows.
Numbers cited here come from `src/hepatiq/validation/report.md` and `models/candidates/training_metrics.json`.

## Cohort and data

- **Single historical cohort.** Everything is trained and evaluated on the Mayo Clinic PBC
  dataset (1974–1984). Treatment standards, assay methods, and patient populations have
  changed since; performance elsewhere is unproven.
- **Small sample.** 418 canonical records, 329 after the 5-year outcome filter (89 patients
  censored before 5 years were excluded). With 132 events, every confidence interval is
  wide — out-of-fold ROC-AUC is **0.8828 [0.8409, 0.9185]**, and intervals this wide mean
  the true value on new patients could plausibly sit anywhere in that band. V1 now reads
  canonical `data/external/pbc.csv` (418 rows) with pinned SHA-256 provenance;
  `data/raw/pbc.csv` is retained only as archived lineage. Its extra row (id 419) is
  censored before 5 years and changes no labels.
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
- **The Mayo Risk Score is computable and is now benchmarked (v2).** Its five
  inputs — age, bilirubin, albumin, prothrombin time, and edema — are all present
  in the cohort, so the claim that the missing labs block it was wrong. Only MELD
  remains impossible (no INR or creatinine). GLOBE and UK-PBC still require
  external cohorts or post-UDCA treated patients and remain future work.
- **`survival::pbc` is the Dickson 1989 cohort itself.** The 312 randomized
  patients are the score's derivation set and the 106 non-randomized patients are
  its published independent validation set. Consequently:
  - the full-cohort Mayo Risk Score AUC (0.886) is *apparent*, not external;
  - v1 has **no truly external validation**, because the 106 were part of its
    training data;
  - the only honest head-to-head is to retrain v1 on the 312 and test on the 106.
- **Held-out result (n=70 with a complete score, 33 events):** fixed Mayo Risk
  Score AUC **0.851** vs retrained v1 pipeline **0.816** (c-index 0.775 vs
  0.731). The confidence intervals overlap, so neither is proven superior — but
  v1's apparent advantage does not survive held-out testing. The 17-feature model
  has not demonstrated added value over a five-variable 1989 score.
- **UDCA is not a clean external validation.** `survival::udca1` is a
  UDCA-treated cohort with a *composite progression* endpoint and short
  follow-up (maximum ~1,896 days), and it stores the Mayo Risk Score without the
  inputs needed to recompute it. Its stored-score c-index is 0.621 (n=169,
  composite endpoint), which is not comparable to the Mayo death/transplant
  endpoint. Full details: [`SCORE_BENCHMARK.md`](SCORE_BENCHMARK.md).

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
  support them additively. Calibration is imperfect and now quantified: OOF Brier
  **0.1364 [0.1136, 0.1632]**, calibration slope **0.725**, CITL **-0.498**, ECE
  **0.062**, and ICI **0.248**. The weighted model overpredicts on average; reliability
  diagrams are in `reports/figures/00_calibration_oof.png` and
  `reports/figures/01_reliability_f17_vs_f5.png`. These are internal OOF estimates,
  not external validation.
- **Composite endpoint.** The target is death *or* liver transplant within 5 years;
  the two have different clinical meanings and are pooled here.

## Software and deployment

- **No authentication or authorization.** The API and UI are open to anyone who can reach
  the port: no login and no identity checks. An in-process per-client rate limiter covers
  prediction, agent, and history requests, but its state resets on restart and is not
  shared across instances. Proxy-header trust must stay off unless a trusted reverse
  proxy sets `X-Forwarded-For`; otherwise clients can pick their own bucket.
  Acceptable for a local demo, not for any deployment handling real patient data
  (which would also need TLS, authentication, PHI controls, encryption at rest, and
  audit logging the project does not implement).
- **Local-only history.** Predictions are logged to a gitignored SQLite file on the
  machine running the server; there is no backup, retention policy, or tamper protection.
- **Model artifact trust boundary.** Startup verifies `model.skops` against the
  SHA-256 and feature contract in `models/model_manifest.json`, then deserializes
  it with skops using a hard-coded extra trusted-type allowlist; skops' own
  library-controlled trusted defaults also apply. This catches accidental
  corruption or replacement and retires the arbitrary-pickle execution risk, but
  the manifest is not a signature: an attacker who can replace both files still
  bypasses the integrity check. Do not load a model from a user upload or
  untrusted URL; use a signed manifest or read-only artifact mount for a stronger
  authenticity boundary.
- **No monitoring.** Nothing tracks prediction drift, input-range violations in
  production, or model degradation over time; the model is a frozen `.skops`
  artifact from one training run.
- **Research prototype status.** Not FDA-approved, CDSCO-approved, or clinically
  validated; not a substitute for physician judgment (see the README disclaimer).

## What the evidence does support

On this cohort, with this pipeline (leakage-controlled 5-fold CV, seed 42), the deployed
Logistic Regression discriminates 5-year severe events substantially better than a
constant baseline, with calibration better than the baseline, and the API's numerical
output is exactly reproducible against direct model inference (asserted in the test
suite). It does **not** outperform the 1989 Mayo Risk Score on held-out patients, and no
external cohort has confirmed either model. That is the claim; nothing beyond it is.
