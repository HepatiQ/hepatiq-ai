# HepatiQ AI

Explainable Clinical Risk Prediction for Primary Biliary Cholangitis

**HepatiQ** is an explainable clinical decision-support web application that estimates 5-year severe event risk (death or liver transplant) for patients with Primary Biliary Cholangitis (PBC) using routine liver function tests and machine learning with SHAP-based interpretability.

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

- **Trained on:** Mayo Clinic Primary Biliary Cholangitis (PBC) dataset — 419 initial patient records; 329 after applying 5-year censoring filter
- **Disease specificity:** PBC is a specific autoimmune liver condition, *not* liver cirrhosis or other hepatic disorders
- **Clinical role:** decision-support aid, not an autonomous diagnostic device or replacement for histological biopsy
- **Target users:** general practitioners, clinical diagnostic labs, medical researchers
- **Target outcome:** 5-year severe event (death or liver transplant), not short-term prognosis

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

## Tech Stack

| Category | Technology |
| --- | --- |
| **Programming** | Python 3.10+ |
| **Database** | SQLite & SQLAlchemy |
| **Frontend** | Streamlit (custom-themed UI) |
| **Backend** | FastAPI & Uvicorn (modular inference API) |
| **ML & Data** | Scikit-learn (IterativeImputer, StandardScaler), Pandas, NumPy, XGBoost |
| **Explainability** | SHAP |
| **Version Control** | Git & GitHub |

### Role Breakdown

| Member | Role | Tools |
| --- | --- | --- |
| **Nirali Verma** | Data & ML Lead | Pandas, NumPy, Scikit-learn, XGBoost, SHAP |
| **Meet Dubey** | Backend & MLOps | FastAPI, Uvicorn, Joblib, GitHub |
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

Explainable Clinical Risk Prediction for Primary Biliary Cholangitis

**HepatiQ** is an explainable clinical decision-support web application that estimates 5-year severe event risk (death or liver transplant) for patients with Primary Biliary Cholangitis (PBC) using routine liver function tests and machine learning with SHAP-based interpretability.

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

- **Trained on:** Mayo Clinic Primary Biliary Cholangitis (PBC) dataset — 419 initial patient records; 329 after applying 5-year censoring filter
- **Disease specificity:** PBC is a specific autoimmune liver condition, *not* liver cirrhosis or other hepatic disorders
- **Clinical role:** decision-support aid, not an autonomous diagnostic device or replacement for histological biopsy
- **Target users:** general practitioners, clinical diagnostic labs, medical researchers
- **Target outcome:** 5-year severe event (death or liver transplant), not short-term prognosis

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

## Tech Stack

| Category | Technology |
| --- | --- |
| **Programming** | Python 3.10+ |
| **Database** | SQLite & SQLAlchemy |
| **Frontend** | Streamlit (custom-themed UI) |
| **Backend** | FastAPI & Uvicorn (modular inference API) |
| **ML & Data** | Scikit-learn (IterativeImputer, StandardScaler), Pandas, NumPy, XGBoost |
| **Explainability** | SHAP |
| **Version Control** | Git & GitHub |

### Role Breakdown

| Member | Role | Tools |
| --- | --- | --- |
| **Nirali Verma** | Data & ML Lead | Pandas, NumPy, Scikit-learn, XGBoost, SHAP |
| **Meet Dubey** | Backend & MLOps | FastAPI, Uvicorn, Joblib, GitHub |
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

* `meet-backend`
* `nirali-ml`
* `deekshitha-frontend`
* `rudra-validation`

The full workflow guidance is in [docs/TEAM_WORKFLOW.md](https://www.google.com/search?q=docs/TEAM_WORKFLOW.md), and the repo includes a simple PR template in [.github/pull_request_template.md](https://www.google.com/search?q=.github/pull_request_template.md).[...]

## Project Goals

1. **Build an automated 5-year severe event predictor** for PBC patients, delivered as a web-accessible tool
2. **Ensure explainability** via SHAP, showing clinicians which biomarker deviations drove each risk score
3. **Achieve stable, defensible performance** by training three regularized models (Logistic Regression, Random Forest, and shallow XGBoost), comparing them on ROC-AUC, precision, recall, F1, and calibration, and reporting confidence intervals rather than point estimates, prioritizing stability over marginal accuracy on a limited-size cohort
4. **Provide intuitive clinical dashboard** for data entry, risk scoring, and visual feature-importance charts
5. **Maintain diagnostic history** via local SQLite logging for audit trails and clinical documentation

## Getting Started

This project is organized into functional folders for team collaboration:

* `ml/` — data cleaning, model training, SHAP generation
* `backend/` — FastAPI application and model serving
* `frontend/` — Streamlit interface
* `validation/` — statistical validation and clinical benchmarking
* `models/` — trained model artifacts (`.pkl` files)
* `data/` — the Mayo Clinic PBC dataset
* `media/` — logo and visual assets
* `docs/` — documentation and project planning

See [docs/GETTING_STARTED.md](https://www.google.com/search?q=docs/GETTING_STARTED.md) for full setup instructions.

## Dataset & Attribution

**Source:** Mayo Clinic Primary Biliary Cholangitis (PBC) trial dataset (1974–1984)
**Initial records:** 419 patients
**After 5-year censoring filter:** 329 patients (90 excluded: censored with outcome unknown)
**Class balance:** 40.1% severe event, 59.9% event-free (near-balanced, uses `class_weight='balanced'` during training)
**License:** Commonly redistributed mirrors (e.g., UCI) are shared under CC BY 4.0, permitting reuse with attribution

## Contributing

This is a **student team project** at Sharda University's Anand School of Engineering & Technology. See [docs/TEAM_WORKFLOW.md](https://www.google.com/search?q=docs/TEAM_WORKFLOW.md) for contribution guidelines.

## Future Work

### Clinical Benchmarking

* Compare HepatiQ against established prognostic tools:
* Mayo Risk Score
* GLOBE Score
* UK-PBC Risk Score



### External Validation

* Evaluate performance on independent PBC cohorts
* Investigate access to:
* Global PBC Study Group datasets
* UK-PBC Registry
* Publicly available clinical trial cohorts



### Model Improvements

* Reliability diagrams and calibration plots
* Cohort percentile ranking
* Risk stratification categories
* Survival analysis extensions:
* Cox Proportional Hazards
* Random Survival Forests
* Time-to-event prediction



### Platform Development

* FastAPI prediction service
* Streamlit clinical dashboard
* Prediction history and reporting tools
* Exportable risk scorecards

## License

This project is under active team development and is intended for collaborative, academic use within the HepatiQ project framework.

---

**Quick links:** [Getting Started](https://www.google.com/search?q=docs/GETTING_STARTED.md) | [Roadmap](https://www.google.com/search?q=docs/ROADMAP.md) | [Workflow](https://www.google.com/search?q=docs/TEAM_WORKFLOW.md)

```

```