# HepatiQ

**HepatiQ** is an explainable clinical decision-support web application that estimates 5-year severe event risk (death or liver transplant) for patients with Primary Biliary Cholangitis (PBC) using routine liver function tests and machine learning with SHAP-based interpretability.

## Overview

Clinicians use Liver Function Tests (LFTs) and blood biochemistry to assess hepatic risk, but manual interpretation of multidimensional physiological data is time-consuming, subject to practitioner variability, and inconsistent across facilities. While machine learning can reliably process these inputs, most deployed clinical AI tools are "black boxes" — they output a probability with no explanation of why, creating a significant barrier to clinical trust and adoption.

**HepatiQ** addresses this by combining regularized machine learning classifiers with SHAP-based Explainable AI (XAI) to predict a patient's probability of a severe event within a 5-year window and show clinicians exactly which biomarkers drove that specific prediction.

### Core Features
- **5-year severe event risk scoring** from five routine biomarkers: Serum Bilirubin, Albumin, Age, Prothrombin Time (PT), and Platelets
- **Interpretable predictions** via SHAP, showing per-patient feature contributions
- **Regularized dual-model ensemble**: Logistic Regression (L1/L2 penalty) and shallow, regularized XGBoost, compared via 5-fold cross-validation
- **Statistical rigor**: confidence intervals (not point estimates), class-balanced training, IterativeImputer for missing data
- **Local diagnostic history**: SQLite logging of patient evaluations and risk scorecards
- **Clean separation** between data pipeline, model serving (FastAPI), and UI (Streamlit)

## Problem Statement

* **Manual data evaluation:** interpreting complex LFT panels is labor-intensive and subject to practitioner interpretation bias
* **The "black box" problem:** existing AI diagnostic tools output a probability score without explaining why, limiting clinical adoption
* **Inconsistent risk staging:** clinics without specialized hepatology expertise struggle to produce uniform, interpretable risk assessments

## Scope & Limitations

- **Trained on:** Mayo Clinic Primary Biliary Cholangitis (PBC) dataset — 419 initial patient records; 329 after applying 5-year censoring filter
- **Disease specificity:** PBC is a specific autoimmune liver condition, *not* liver cirrhosis or other hepatic disorders
- **Clinical role:** decision-support aid, not an autonomous diagnostic device or replacement for histological biopsy
- **Target users:** general practitioners, clinical diagnostic labs, medical researchers
- **Target outcome:** 5-year severe event (death or liver transplant), not short-term prognosis

## Tech Stack

| Category | Technology |
|----------|-----------|
| **Programming** | Python 3.10+ |
| **Database** | SQLite & SQLAlchemy |
| **Frontend** | Streamlit (custom-themed UI) |
| **Backend** | FastAPI & Uvicorn (modular inference API) |
| **ML & Data** | Scikit-learn (IterativeImputer, StandardScaler), Pandas, NumPy, XGBoost |
| **Explainability** | SHAP |
| **Version Control** | Git & GitHub |

### Role Breakdown

| Member | Role | Tools |
|--------|------|-------|
| **Nirali Verma** | Data & ML Lead | Pandas, NumPy, Scikit-learn, XGBoost, SHAP |
| **Pranjal Dubey** | Backend & MLOps | FastAPI, Uvicorn, Joblib, GitHub |
| **Subbannagari Deekshitha** | Frontend UI | Streamlit, Requests, Plotly |
| **Rudra Singh Tomar** | Clinical Validation | SciPy, Statsmodels, Scikit-learn |

## System Flow

```
User Input                 Backend Processing            Output
(Streamlit UI)             (FastAPI + Model)             (Dashboard)
       ↓                           ↓                            ↓
Clinician enters        1. Load regularized model    Risk scorecard with:
lab values              2. Preprocess (StandardScaler) • 5-year risk probability
  (5 biomarkers)        3. Generate SHAP values        • Per-feature SHAP chart
       │                4. Log to SQLite               • Clinical interpretation
       │                                               • Diagnostic history
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

- Keep `main` as the stable branch
- Work on a feature branch for your task
- Open a pull request before merging
- Keep PRs small and easy to review
- Use short, readable branch names

Examples:

- `pranjal-backend`
- `nirali-ml`
- `deekshitha-frontend`
- `rudra-validation`

The full workflow guidance is in [docs/TEAM_WORKFLOW.md](docs/TEAM_WORKFLOW.md), and the repo includes a simple PR template in [.github/pull_request_template.md](.github/pull_request_template.md).[...]

## Project Goals

1. **Build an automated 5-year severe event predictor** for PBC patients, delivered as a web-accessible tool
2. **Ensure explainability** via SHAP, showing clinicians which biomarker deviations drove each risk score
3. **Achieve stable, defensible performance** by training two regularized models (Logistic Regression + shallow XGBoost) and reporting confidence intervals, prioritizing stability over marginal accuracy on a limited-size cohort
4. **Provide intuitive clinical dashboard** for data entry, risk scoring, and visual feature-importance charts
5. **Maintain diagnostic history** via local SQLite logging for audit trails and clinical documentation

## Getting Started

This project is organized into functional folders for team collaboration:

- `ml/` — data cleaning, model training, SHAP generation
- `backend/` — FastAPI application and model serving
- `frontend/` — Streamlit interface
- `validation/` — statistical validation and clinical benchmarking
- `models/` — trained model artifacts (`.pkl` files)
- `data/` — the Mayo Clinic PBC dataset
- `media/` — logo and visual assets
- `docs/` — documentation and project planning

See [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) for full setup instructions.

## Dataset & Attribution

**Source:** Mayo Clinic Primary Biliary Cholangitis (PBC) trial dataset (1974–1984)  
**Initial records:** 419 patients  
**After 5-year censoring filter:** 329 patients (90 excluded: censored with outcome unknown)  
**Class balance:** 40.1% severe event, 59.9% event-free (near-balanced, uses `class_weight='balanced'` during training)  
**License:** Commonly redistributed mirrors (e.g., UCI) are shared under CC BY 4.0, permitting reuse with attribution

## Contributing

This is a **student team project** at Sharda University's Anand School of Engineering & Technology. See [docs/TEAM_WORKFLOW.md](docs/TEAM_WORKFLOW.md) for contribution guidelines.

## License

This project is under active team development and is intended for collaborative, academic use within the HepatiQ project framework.

---

**Quick links:** [Getting Started](docs/GETTING_STARTED.md) | [Roadmap](docs/ROADMAP.md) | [Workflow](docs/TEAM_WORKFLOW.md)
