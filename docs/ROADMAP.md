# HepatiQ Roadmap

A 50-day build plan across four workstreams. Each phase lists what's due and who owns it. Currently in **Phase 4 (Days 31–40)**.

## Phase 1 — Foundation (Days 1–10)
- Repo setup, environment, role assignment
- Acquire and explore the Mayo Clinic PBC dataset (Nirali)
- Document the dataset's scope up front: PBC is a specific autoimmune liver condition, not cirrhosis in general — stated early so it shapes the model, the UI copy, and the final report rather than being added as an afterthought
- Define the API contract (input fields, response shape) so backend and frontend can build against it independently (Pranjal + Deekshitha)

## Phase 2 — Model Development (Days 11–20)
- Missing-value imputation (`IterativeImputer`) and feature scaling (`StandardScaler`) pipeline (Nirali)
- Train Logistic Regression, Random Forest, and shallow regularized XGBoost, compared with 5-fold stratified cross-validation on ROC-AUC, precision, recall, F1, and Brier score
- Select and lock the final model by CV performance; export as `.pkl` via joblib

## Phase 3 — Backend & Integration (Days 21–30)
- FastAPI service with a `/predict` endpoint and Pydantic request/response models (Pranjal)
- Load the trained model with joblib
- Streamlit skeleton wired to the live API (Deekshitha)
- Rudra's statistical validation can start here, in parallel with backend/frontend work — see note below

## Phase 4 — Explainability & Visualization (Days 31–40) — complete
- SHAP integration in the backend, returned alongside each prediction
- Chart rendering in Streamlit — Plotly or Altair for interactivity, rather than static matplotlib
- Rudra's validation work continues in parallel

## Phase 5 — Validation, Documentation & Delivery (Days 41–50) — complete
- **Days 41–45:** bootstrap confidence intervals, Brier score comparison, and the OOF
  validation runner with a class-prior baseline (Rudra) — see decision note below — done
- **Days 46–50:** end-to-end testing, limitations write-up, final polish, demo/presentation
  prep — kept as its own block so packaging the project doesn't get squeezed by validation
  running late — done
  - Final polish shipped: risk-band badge, training-range extrapolation warnings, latency +
    model-version display, history limit/Clear controls, dark clinical theme with logo,
    research-prototype disclaimer footer, pinned dependencies, CI coverage floor raised to 60
    (62 tests, ~63% coverage)

## Changes from the original plan, and why

- **Reinstated three models instead of two.** An earlier version of this plan dropped XGBoost in favor of just Logistic Regression + Random Forest, reasoning that tuning a third model's hyperparameters wasn't worth it on a 329-patient cohort. That reasoning was sound in the abstract, but once all three were actually trained and cross-validated (5-fold, imputation + scaling fit inside each fold to avoid leakage), the real numbers argued for keeping all three rather than assuming the answer up front. Random Forest edges out the highest mean ROC-AUC (0.887 vs. Logistic Regression's 0.880 and XGBoost's 0.870), but its 95% CI (0.828–0.946) overlaps Logistic Regression's almost entirely (0.837–0.923) — on a cohort this size, that gap isn't statistically decisive.
- **Winner: Logistic Regression**, selected by a documented rule (`ml/train.py::select_winner`) rather than a bare ROC-AUC argmax: since the top models' CIs overlap, selection falls through to clinical/statistical tie-breakers in order — recall (LR and RF tie exactly at 0.8105), then calibration (LR's Brier 0.136 beats RF's 0.141), which is where LR wins outright. LR also has higher precision (0.767 vs. 0.728) and more stable recall across folds. Full fold-by-fold numbers are in `models/training_metrics.json`.
- **Rudra's validation track moves earlier.** Statistical validation depends on the model being locked (end of Phase 2), not on SHAP or the frontend being finished. Running it in parallel with Phases 3–4 instead of strictly after them removes a bottleneck in the last 10 days, which is normally the most time-pressured stretch of a project like this.
- **Days 46–50 are protected as a buffer.** Testing, limitations documentation, and demo prep are distinct from the statistics work itself and are easy to underestimate — giving them a dedicated block avoids a last-minute scramble.
- **MELD benchmarking replaced by a class-prior baseline.** The original plan called for comparing the model against the MELD score, but MELD requires bilirubin, INR **and creatinine**, and the Mayo PBC dataset has no INR or creatinine columns. Constructing a "MELD" from protime plus a fabricated creatinine would produce a non-clinical number wearing a clinical name — worse than having no benchmark at all. Instead, `validation/run_validation.py` reports 5-fold OOF metrics with 95% bootstrap CIs against a class-prior baseline (predicts the training-fold prevalence; AUC ≈ 0.5 by construction). Result: OOF ROC-AUC 0.8828 [0.8409, 0.9185] vs. baseline 0.4924 — the model clearly beats naive guessing. If a clinical benchmark is ever wanted, it needs a dataset that carries creatinine and INR (e.g. MELD's original Mayo/VA cohorts), not this one.