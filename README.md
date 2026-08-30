# HepatiQ

HepatiQ is a clinical decision-support web application that estimates mortality risk for patients with Primary Biliary Cholangitis (PBC), a chronic liver disease, using routine lab values and an ex[...]

## Overview

Clinicians often have to weigh several lab markers at once to judge how serious a patient's liver disease is. HepatiQ takes that judgment call and grounds it in a model trained on real outcomes dat[...]

### Core Features
- Mortality risk scoring from five routine lab inputs: Bilirubin, Albumin, Age, Prothrombin Time, and Platelets
- SHAP-based explainability charts showing each feature's contribution to the prediction
- Statistically validated performance (bootstrap confidence intervals, MELD score benchmarking)
- Clean separation between model, API, and UI layers for maintainability

## Problem We Solve

Most clinical AI tools are black boxes — they output a score with no visibility into why. That's a hard sell in medicine, where a doctor needs to trust and verify a recommendation before acting [...]

## Scope & Limitations

HepatiQ is trained on the Mayo Clinic Primary Biliary Cholangitis (PBC) dataset — a specific autoimmune liver condition, not liver cirrhosis in general. Predictions should be understood as speci[...]

## Tech Stack

### Data & ML (Nirali)
- Pandas & NumPy — data loading and cleaning
- Scikit-learn — `IterativeImputer` for missing values, `StandardScaler`, Penalized Logistic Regression, Random Forest
- SHAP — model explainability

### Backend API (Meet)
- FastAPI — REST API, with Pydantic models for request/response validation
- Uvicorn — ASGI server
- Joblib — loading trained models into memory
- GitHub — repository and version control (`hepatiq-ai`)

### Frontend UI (Deekshitha)
- Streamlit — interactive web interface
- Requests — communication with the FastAPI backend

### Validation & Clinical Benchmarking (Rudra)
- SciPy / Statsmodels — bootstrap confidence intervals
- Scikit-learn — Brier score, stratified cross-validation
- MELD score — clinical baseline for comparison
- Markdown — clinical limitations documentation

### DevOps and Collaboration
- GitHub (`hepatiq-ai`)
- Team-based, phased development (see [docs/ROADMAP.md](docs/ROADMAP.md))

## System Flow
1. A clinician enters a patient's lab values (Bilirubin, Albumin, Age, Prothrombin Time, Platelets) in the Streamlit interface.
2. Streamlit sends the input to the FastAPI backend via a REST request.
3. The backend loads the trained model and computes a mortality risk score.
4. SHAP values are computed for the prediction and returned alongside the score.
5. Streamlit renders the risk score and an explainability chart showing each feature's contribution.

## Team

| Name | Role | Focus Area |
| --- | --- | --- |
| Nirali | Data & ML Lead | Data cleaning, model training, SHAP integration |
| Meet | Backend & MLOps / Repo Management | FastAPI, model serving, GitHub organization |
| Deekshitha | Frontend UI | Streamlit interface, UX |
| Rudra | Clinical Validation | Statistical testing, MELD benchmarking, documentation |

## Repository Workflow

This repository follows a simple branch-based workflow so the team can stay organized without making things heavy.

- Keep `main` as the stable branch
- Work on a feature branch for your task
- Open a pull request before merging
- Keep PRs small and easy to review
- Use short, readable branch names

Examples:

- `meet-backend`
- `nirali-ml`
- `deekshitha-frontend`
- `rudra-validation`

The full workflow guidance is in [docs/TEAM_WORKFLOW.md](docs/TEAM_WORKFLOW.md), and the repo includes a simple PR template in [.github/pull_request_template.md](.github/pull_request_template.md).[...]

## Goals
- Build a functional, interpretable clinical risk tool
- Validate model performance against the MELD score baseline
- Deliver interactive SHAP visualizations
- Complete within a 50-day roadmap

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

HepatiQ trains on the Mayo Clinic PBC trial dataset (1974–1984, 418 patients). Commonly redistributed mirrors of this dataset (e.g. via UCI) are shared under CC BY 4.0, which permits reuse with[...]

## License

This project is currently under active team development and is intended for collaborative, academic use within the HepatiQ project.
