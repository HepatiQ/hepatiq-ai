# HepatiQ AI

Explainable Clinical Risk Prediction for Primary Biliary Cholangitis

**HepatiQ** is an explainable clinical decision-support web application that estimates 5-year severe event risk (death or liver transplant) for patients with Primary Biliary Cholangitis (PBC) using routine liver function tests and machine learning with SHAP-based interpretability.

> **Version 2 — clinical rebuild.** V2 replaces the single 5-year classifier with
> a censoring-aware survival model, adds published-score benchmarks and a
> 12-month landmark model, and moves the UI to multipage Streamlit. V2 is now
> merged into `main`. V2 is designed, created, and maintained solely by
> **Pranjal Dubey**; v1 was a team project. See [AUTHORS.md](AUTHORS.md). V1
> remains runnable for comparison.
>
> **Phase 1 benchmark (done).** On the 106 held-out Mayo patients, the fixed
> 1989 Mayo Risk Score reaches 5-year AUC **0.851**; the v1 pipeline retrained on
> the 312 derivation patients reaches **0.816** (overlapping CIs, 70 patients /
> 33 events). V1's apparent advantage does not survive held-out testing. Details:
> [`docs/SCORE_BENCHMARK.md`](docs/SCORE_BENCHMARK.md).

## 🚀 Live Demo

- **Web App (Streamlit):** [https://hepatiq-ai.streamlit.app](https://hepatiq-ai.streamlit.app)
- **Backend API (Render):** [https://hepatiq-ai.onrender.com](https://hepatiq-ai.onrender.com)
- **API Docs (Swagger):** [https://hepatiq-ai.onrender.com/docs](https://hepatiq-ai.onrender.com/docs)

## Overview

Clinicians use Liver Function Tests (LFTs) and blood biochemistry to assess hepatic risk, but manual interpretation of multidimensional physiological data is time-consuming, subject to practitioner variability, and inconsistent across facilities. While machine learning can reliably process these inputs, most deployed clinical AI tools are "black boxes" — they output a probability with no explanation of why, creating a significant barrier to clinical trust and adoption.

## Research Disclaimer

HepatiQ is an academic research project and clinical decision-support prototype.

It is not an FDA-approved, CDSCO-approved, or clinically validated medical device and must not be used as a substitute for physician judgment, diagnosis, or treatment decisions.

**HepatiQ** addresses this by combining regularized machine learning classifiers with SHAP-based Explainable AI (XAI) to predict a patient's probability of a severe event within a 5-year window and show clinicians exactly which biomarkers drove that specific prediction.

- **5-year severe event risk scoring** using 17 routinely collected clinical and biochemical variables from the Mayo Clinic PBC cohort, enabling risk estimation from standard patient and laboratory data.
- **Interpretable predictions** via SHAP, showing per-patient feature contributions
- **Three-model benchmarking framework**: Logistic Regression, Random Forest, and shallow regularized XGBoost evaluated via 5-fold stratified cross-validation using ROC-AUC, precision, recall, F1 score, and Brier score. Logistic Regression was selected as the final deployment model due to its strong calibration, competitive discrimination performance, and clinical interpretability.
- **Statistical rigor**: confidence intervals (not point estimates), class-balanced training, IterativeImputer + StandardScaler fit inside each CV fold (not upfront) to avoid leaking held-out patients into preprocessing
- **Local diagnostic history**: SQLite logging of patient evaluations and risk scorecards
- **Clean separation** between data pipeline, model serving (FastAPI), and UI (Streamlit)

## Problem Statement

- **Manual data evaluation:** interpreting complex LFT panels is labor-intensive and subject to practitioner interpretation bias
- **The "black box" problem:** existing AI diagnostic tools output a probability score without explaining why, limiting clinical adoption
- **Inconsistent risk staging:** clinics without specialized hepatology expertise struggle to produce uniform, interpretable risk assessments

## Scope & Limitations

- **Trained on:** canonical `survival::pbc` Mayo Clinic Primary Biliary Cholangitis dataset — 418 patient records; 329 after applying the 5-year censoring filter
- **Disease specificity:** PBC is a specific autoimmune liver condition, *not* liver cirrhosis or other hepatic disorders
- **Clinical role:** decision-support aid, not an autonomous diagnostic device or replacement for histological biopsy
- **Target users:** general practitioners, clinical diagnostic labs, medical researchers
- **Target outcome:** 5-year severe event (death or liver transplant), not short-term prognosis
- **Known limits:** see [docs/LIMITATIONS.md](docs/LIMITATIONS.md) for what the evidence does and does not support

## Current Model Performance

### Final Selected Model

**Logistic Regression**

Three candidate models were evaluated using 5-fold stratified cross-validation:

- Logistic Regression
- Random Forest
- XGBoost

Although Random Forest achieved a marginally higher mean ROC-AUC, Logistic Regression demonstrated the best overall balance of discrimination, calibration, precision, F1 score, and clinical interpretability. Due to its superior calibration and transparency, Logistic Regression was selected as the final HepatiQ deployment model.

### Cross-Validation Results

| Metric | Logistic Regression | Random Forest | XGBoost |
| --- | ---: | ---: | ---: |
| ROC-AUC | 0.8800 | 0.8844 | 0.8706 |
| Precision | 0.7675 | 0.7235 | 0.7225 |
| Recall | 0.8105 | 0.8256 | 0.7880 |
| F1 Score | 0.7861 | 0.7694 | 0.7508 |
| Brier Score ↓ | 0.1363 | 0.1419 | 0.1528 |

Note: Lower Brier Score indicates better probability calibration.

**Out-of-fold estimates** (n=329, 132 events, leakage-controlled): ROC-AUC
**0.8828 [0.8409, 0.9185]** and Brier **0.1364 [0.1136, 0.1632]**. OOF
calibration slope is 0.725, CITL -0.498, ECE 0.062, and ICI 0.248; the weighted
model overpredicts on average. Reliability diagrams are in
[`reports/figures/`](reports/figures/). These are internal OOF estimates, not
external validation.

## Tech Stack

| Category | Technology |
| --- | --- |
| **Programming** | Python 3.12+ |
| **Database** | SQLite (Python stdlib sqlite3) |
| **Frontend** | Streamlit (custom-themed UI) |
| **Backend** | FastAPI & Uvicorn (modular inference API) |
| **ML & Data** | Scikit-learn (IterativeImputer, StandardScaler), skops, Pandas, NumPy, XGBoost |
| **Explainability** | SHAP |
| **Version Control** | Git & GitHub |

### Role Breakdown

| Member | Role | Tools |
| --- | --- | --- |
| **Nirali Verma** | Data & ML Lead | Pandas, NumPy, Scikit-learn, XGBoost, SHAP |
| **Pranjal Dubey** | Backend & MLOps | FastAPI, Uvicorn, skops, GitHub |
| **Subbannagari Deekshitha** | Frontend UI | Streamlit, Requests, Plotly |
| **Rudra Singh Tomar** | Clinical Validation | SciPy, Statsmodels, Scikit-learn |

## System Flow

```text
User Input                 Backend Processing            Output
(Streamlit UI)             (FastAPI + Model)             (Dashboard)
       ↓                                 ↓                            ↓
Clinician enters        1. Load regularized model    Risk scorecard with:
lab values              2. Preprocess (StandardScaler) • 5-year risk probability
(17 clinical and                                       • Per-feature SHAP chart
biochemical variables)  3. Generate SHAP values        • Clinical interpretation
       │                4. Log to SQLite               • Diagnostic history
       │                                                              
       └──────────────────────────┬────────────────────────────┘
                              REST API (/predict)
```

1. Clinician enters patient demographics and LFT biomarkers in Streamlit
2. Streamlit sends POST request to FastAPI backend
3. Backend applies preprocessing (imputation, standardization) and loads regularized model
4. Model predicts 5-year severe event probability
5. SHAP computes per-feature attributions for that patient
6. Streamlit renders risk scorecard + explainability visualization
7. Prediction logged to local SQLite for diagnostic history

## Repository Workflow

This repository follows a simple branch-based workflow so the team can stay organized without making things heavy.

* Keep `main` as the stable branch
* Work on a feature branch for your task
* Open a pull request before merging
* Keep PRs small and easy to review
* Use short, readable branch names

Examples:

* `pranjal-backend`
* `nirali-ml`
* `deekshitha-frontend`
* `rudra-validation`

The full workflow guidance is in [docs/TEAM_WORKFLOW.md](docs/TEAM_WORKFLOW.md), and the repo includes a simple PR template in [.github/pull_request_template.md](.github/pull_request_template.md).

## Project Goals

1. **Build an automated 5-year severe event predictor** for PBC patients, delivered as a web-accessible tool
2. **Ensure explainability** via SHAP, showing clinicians which biomarker deviations drove each risk score
3. **Achieve stable, defensible performance** by training three regularized models (Logistic Regression, Random Forest, and shallow XGBoost), comparing them on ROC-AUC, precision, recall, F1, and calibration, and reporting confidence intervals rather than point estimates, prioritizing stability over marginal accuracy on a limited-size cohort
4. **Provide intuitive clinical dashboard** for data entry, risk scoring, and visual feature-importance charts
5. **Maintain diagnostic history** via local SQLite logging for audit trails and clinical documentation

## Getting Started

This project is organized as an installable Python package for team collaboration:

```text
src/hepatiq/
  backend/     FastAPI application and model serving
  frontend/    Streamlit interface (+ assets/)
  ml/          data cleaning, cohort building, model training, SHAP
  validation/  statistical validation and out-of-fold benchmarking
  paths.py     single source of truth for data/model paths
data/
  external/    canonical survival exports + pinned provenance
  raw/         archived augmented Mayo input (not used for training)
  processed/   labeled 5-year target cohort
  interim/     imputed / scaled exploration artifacts
models/
  model.skops           deployed pipeline (skops, fixed extra trusted types)
  model_manifest.json   artifact hash, feature contract, training metrics
  candidates/           losing models + training metrics
tests/         pytest suite (API, ML guards, validation, Streamlit)
docs/          documentation and project planning
```

Path setup:

```bash
pip install -r requirements.txt
pip install -e . --no-deps
```

**Rate limiting:** the backend applies an in-memory sliding-window limit to
`/predict`, `/agent/reason`, and the history endpoints. Defaults are 60 requests
per 60 seconds per client. Configure with `HEPATIQ_RATE_LIMIT_REQUESTS`,
`HEPATIQ_RATE_LIMIT_WINDOW_SECONDS`, and `HEPATIQ_TRUST_PROXY_HEADERS`. State is
per process, so a multi-instance deployment needs a shared store such as Redis.
Enable proxy-header trust only behind a trusted reverse proxy that sets
`X-Forwarded-For`; clients can otherwise choose their own bucket.

**Model integrity:** startup verifies `models/model.skops` against the SHA-256 and
17-feature contract in `models/model_manifest.json`, then deserializes it through
skops with a hard-coded extra trusted-type allowlist (skops' library-controlled
defaults also apply). Verification and loading use the
same byte snapshot. A missing, malformed, mismatched, or unexpectedly typed
artifact leaves `/health` at 200 with `model_loaded: false` and makes `/predict`
return 503. The manifest detects accidental or tampered replacement but is not a
signature; never load a model from an untrusted upload or URL.

See [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) for full setup instructions.

## Dataset & Attribution

**Primary cohort (v1 and v2):** canonical `survival::pbc` — **418** Mayo Clinic PBC
patients (1974–1984), 312 of them randomized in the D-penicillamine vs placebo
trial. `trt` is `1 = D-penicillamine`, `2 = placebo`; the cohort **predates
UDCA**, so it describes pre-UDCA natural history.
**Longitudinal cohort:** `survival::pbcseq` — 1945 serial visits for the same
312 randomized patients.
**External benchmark cohort:** `survival::udca` — 170 patients from the Lindor
et al. 1994 UDCA trial, with a stored Mayo Risk Score.

These CSVs live in [`data/external/`](data/external/README.md) and are exported
from CRAN `survival` 3.8-12 with pinned SHA-256 provenance. `pbcseq` is **not**
an independent cohort; do not call a `pbc` → `pbcseq` comparison external
validation.

**Dickson 1989 provenance.** `survival::pbc` *is* the cohort used to derive the
Mayo Risk Score: the **312 randomized** patients are its derivation set and the
**106 non-randomized** patients are its published independent validation set.
The score was therefore derived on this data, so its full-cohort AUC (0.886) is
apparent. The 106 patients are the only held-out set available — but they were
part of v1's training data, so v1 has no external validation.

> **v1 data note:** V1 now trains from canonical `data/external/pbc.csv` (418
> rows) and verifies pinned SHA-256 provenance before reading. `data/raw/pbc.csv`
> (419 rows) is retained only as archived lineage: its extra sparse row
> (`id = 419`, no treatment arm, censored at 985 days) is dropped by the 5-year
> filter. Canonical `age` keeps full precision while the raw copy rounds it to 8
> decimals; labels, the 329-patient cohort, and metrics are unchanged.
> Frozen-model predictions moved by less than `5e-11`, and the model was not
> retrained.

**v1 5-year filter:** 329 patients (89 censored before 5 years, outcome unknown)
**Class balance (v1):** 40.1% severe event, 59.9% event-free (`class_weight='balanced'`)
**License:** `survival` is LGPL (>= 2); datasets are redistributed from published
sources — cite Dickson 1989, Murtaugh 1994, and Lindor 1994 (see
[data/external/README.md](data/external/README.md)).

## Contributing

This is a **student team project** at Sharda University's Anand School of Engineering & Technology. See [docs/TEAM_WORKFLOW.md](docs/TEAM_WORKFLOW.md) for contribution guidelines.

## Future Work

### Clinical Benchmarking

* Compare HepatiQ against established prognostic tools:
* ~~Mayo Risk Score~~ — implemented and benchmarked in
  [`docs/SCORE_BENCHMARK.md`](docs/SCORE_BENCHMARK.md)
* GLOBE Score (requires post-UDCA treatment response; not computable here)
* UK-PBC Risk Score (requires an external UK registry cohort)



### External Validation

* Evaluate performance on independent PBC cohorts
* Investigate access to:
* Global PBC Study Group datasets
* UK-PBC Registry
* Publicly available clinical trial cohorts



### Model Improvements

* ~~Reliability diagrams and calibration plots~~ — implemented in
  [`reports/figures/`](reports/figures/)
* Cohort percentile ranking
* Risk stratification categories
* Survival analysis extensions:
* Cox Proportional Hazards
* Random Survival Forests
* Time-to-event prediction



### Platform Development

* Exportable risk scorecards

## License

This project is under active team development and is intended for collaborative, academic use within the HepatiQ project framework.

---

**Quick links:** [Getting Started](docs/GETTING_STARTED.md) | [Roadmap](docs/ROADMAP.md) | [Workflow](docs/TEAM_WORKFLOW.md)
