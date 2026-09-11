# HepatiQ Roadmap

A 50-day build plan across four workstreams. Each phase lists what's due and who owns it. Currently in **Phase 4 (Days 31–40)**.

## Phase 1 — Foundation (Days 1–10)
- Repo setup, environment, role assignment
- Acquire and explore the Mayo Clinic PBC dataset (Nirali)
- Document the dataset's scope up front: PBC is a specific autoimmune liver condition, not cirrhosis in general — stated early so it shapes the model, the UI copy, and the final report rather tha[...]
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

## Phase 4 — Explainability & Visualization (Days 31–40) — current phase
- SHAP integration in the backend, returned alongside each prediction
- Chart rendering in Streamlit — Plotly or Altair for interactivity, rather than static matplotlib
- Rudra's validation work continues in parallel

## Phase 5 — Validation, Documentation & Delivery (Days 41–50)
- **Days 41–45:** finish bootstrap confidence intervals, MELD score benchmarking, Brier score comparison (Rudra)
- **Days 46–50:** end-to-end testing, limitations write-up, final polish, demo/presentation prep — kept as its own block so packaging the project doesn't get squeezed by validation running lat[...]

## Changes from the original plan, and why

- **Reinstated three models instead of two.** An earlier version of this plan dropped XGBoost in favor of just Logistic Regression + Random Forest, reasoning that tuning a third model's hyperparameters wasn't worth it on a 329-patient cohort. That reasoning was sound in the abstract, but once all three were actually trained and cross-validated (5-fold, imputation + scaling fit inside each fold to avoid leakage), the real numbers argued for keeping all three rather than assuming the answer up front. Random Forest edges out the highest mean ROC-AUC (0.887 vs. Logistic Regression's 0.880 and XGBoost's 0.870), but its 95% CI (0.828–0.946) overlaps Logistic Regression's almost entirely (0.837–0.923) — on a cohort this size, that gap isn't statistically decisive.
- **Winner: Logistic Regression**, selected by a documented rule (`ml/train.py::select_winner`) rather than a bare ROC-AUC argmax: since the top models' CIs overlap, selection falls through to clinical/statistical tie-breakers in order — recall (LR and RF tie exactly at 0.8105), then calibration (LR's Brier 0.136 beats RF's 0.141), which is where LR wins outright. LR also has higher precision (0.767 vs. 0.728) and more stable recall across folds. Full fold-by-fold numbers are in `models/training_metrics.json`.
- **Rudra's validation track moves earlier.** Statistical validation depends on the model being locked (end of Phase 2), not on SHAP or the frontend being finished. Running it in parallel with Pha[...]
- **Days 46–50 are protected as a buffer.** Testing, limitations documentation, and demo prep are distinct from the statistics work itself and are easy to underestimate — giving them a dedicat[...]