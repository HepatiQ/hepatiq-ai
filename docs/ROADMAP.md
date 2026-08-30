# HepatiQ Roadmap

A 50-day build plan across four workstreams. Each phase lists what's due and who owns it. Currently in **Phase 4 (Days 31–40)**.

## Phase 1 — Foundation (Days 1–10)
- Repo setup, environment, role assignment
- Acquire and explore the Mayo Clinic PBC dataset (Nirali)
- Document the dataset's scope up front: PBC is a specific autoimmune liver condition, not cirrhosis in general — stated early so it shapes the model, the UI copy, and the final report rather than being added as an afterthought
- Define the API contract (input fields, response shape) so backend and frontend can build against it independently (Meet + Deekshitha)

## Phase 2 — Model Development (Days 11–20)
- Missing-value imputation (`IterativeImputer`) and feature scaling (`StandardScaler`) pipeline (Nirali)
- Train Penalized Logistic Regression and Random Forest with stratified cross-validation
- Select and lock the final model; export as `.pkl` via joblib

## Phase 3 — Backend & Integration (Days 21–30)
- FastAPI service with a `/predict` endpoint and Pydantic request/response models (Meet)
- Load the trained model with joblib
- Streamlit skeleton wired to the live API (Deekshitha)
- Rudra's statistical validation can start here, in parallel with backend/frontend work — see note below

## Phase 4 — Explainability & Visualization (Days 31–40) — current phase
- SHAP integration in the backend, returned alongside each prediction
- Chart rendering in Streamlit — Plotly or Altair for interactivity, rather than static matplotlib
- Rudra's validation work continues in parallel

## Phase 5 — Validation, Documentation & Delivery (Days 41–50)
- **Days 41–45:** finish bootstrap confidence intervals, MELD score benchmarking, Brier score comparison (Rudra)
- **Days 46–50:** end-to-end testing, limitations write-up, final polish, demo/presentation prep — kept as its own block so packaging the project doesn't get squeezed by validation running late

## Changes from the original plan, and why

- **Two models instead of three.** Dropping XGBoost in favor of just Penalized Logistic Regression and Random Forest is the right call for a 418-patient dataset — tuning a third model's hyperparameters on small cross-validation folds adds noise without much real signal. That time is better spent on confidence intervals than on an extra model.
- **Rudra's validation track moves earlier.** Statistical validation depends on the model being locked (end of Phase 2), not on SHAP or the frontend being finished. Running it in parallel with Phases 3–4 instead of strictly after them removes a bottleneck in the last 10 days, which is normally the most time-pressured stretch of a project like this.
- **Days 46–50 are protected as a buffer.** Testing, limitations documentation, and demo prep are distinct from the statistics work itself and are easy to underestimate — giving them a dedicated block avoids a last-minute scramble.
