# Conference abstract and poster outline

## Proposed title

Explainable 5-year risk estimation in primary biliary cholangitis: internal performance and held-out benchmark of a research prototype

## Abstract

Primary biliary cholangitis (PBC) prognosis has historically been summarized by the five-variable Mayo Risk Score. Machine-learning models may use more routine laboratory variables, but their added value must be tested against published scores on held-out patients. We built HepatiQ, an explainable research prototype that estimates 5-year death-or-transplant risk from 17 clinical and biochemical variables using a regularized logistic-regression pipeline with multiple imputation, standardization, and SHAP attributions. The model was selected from three candidates by a documented rule using cross-validated discrimination and Brier score. In the canonical `survival::pbc` cohort, 329 patients had known 5-year outcomes (132 events). Leakage-controlled out-of-fold ROC-AUC was 0.8828 [0.8409, 0.9185] versus 0.4924 [0.4277, 0.5514] for a class-prior baseline; calibration was imperfect (slope 0.725, CITL -0.498). For held-out evaluation, the v1 pipeline was retrained on the 312 randomized patients and tested on the 106 non-randomized patients, the original validation set of the Mayo Risk Score. Among 70 patients with a complete score and 33 events, the fixed Mayo Risk Score reached AUC 0.851 [0.749, 0.928] and HepatiQ reached 0.816 [0.712, 0.905]. The intervals overlap; the 17-feature model did not demonstrate added value on held-out patients. The prototype exposes single-patient and batch scoring through a FastAPI service and Streamlit interface, with per-patient SHAP explanations and a frozen, verified model artifact. HepatiQ is research-only, not externally validated, and not a medical device. Its main contribution is a reproducible, transparent workflow for showing both the promise and the limits of clinical ML on a small historical cohort.

## Three takeaways

1. Leakage-safe internal evaluation can look strong while held-out performance fails to beat a simple published score.
2. SHAP makes model behavior inspectable but does not establish causation or clinical utility.
3. A research prototype should ship with its limitations, benchmark, and reproduction commands in the same package as its demo.

## Poster layout

### Panel 1 — Problem

- 5-year death-or-transplant risk in PBC.
- Historical Mayo Risk Score uses five variables.
- Question: does a 17-feature interpretable model add value on held-out patients?

### Panel 2 — Data and model

- Canonical `survival::pbc`, 418 records, 329 with known 5-year outcome.
- 17 features; imputation and scaling inside each fold.
- Logistic Regression selected over Random Forest and XGBoost using Brier tie-break.

### Panel 3 — Internal evaluation

- Table: OOF AUC, Brier, class-prior baseline.
- Figure: `reports/figures/00_calibration_oof.png`.
- Caption: internal estimate only; calibration imperfect.

### Panel 4 — Held-out benchmark

- Table: Mayo 0.851 vs HepatiQ 0.816.
- Figure: `reports/figures/09_mayo_discrimination.png`.
- Caption: n=70, 33 events, overlapping CIs; no demonstrated added value.

### Panel 5 — Explainability and software

- Example SHAP tornado from `reports/figures/05_patient_b_tornado.png`.
- FastAPI endpoints and Streamlit interface.
- Bulk CSV scoring up to 1,000 rows.

### Panel 6 — Limitations and CTA

- No external validation; no MELD comparison; not a medical device.
- **CTA:** **Try the demo** or **read the model card**.

## Suggested QR-code destinations

- Live demo: `https://hepatiq-ai.streamlit.app`
- API docs: `https://hepatiq-ai.onrender.com/docs`
- Repository: `https://github.com/HepatiQ/hepatiq-ai`
- Technical note: `docs/outreach/TECHNICAL_NOTE.md`
