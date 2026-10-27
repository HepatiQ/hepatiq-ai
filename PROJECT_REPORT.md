# HepatiQ Project Report

## Executive Summary
HepatiQ is an explainable clinical decision-support web application for predicting 5-year severe events (death or liver transplant) in Primary Biliary Cholangitis (PBC) patients using routine liver function tests with ML and SHAP explanations.

**Live Demo:** https://hepatiq-ai.streamlit.app  
**Backend API:** https://hepatiq-ai.onrender.com  
**API Documentation:** https://hepatiq-ai.onrender.com/docs

## Team
- Nirali Verma - Data & ML Lead
- Pranjal Dubey - Backend & MLOps  
- Subbannagari Deekshitha - Frontend UI
- Rudra Singh Tomar - Clinical Validation

## Problem Statement
PBC is a chronic autoimmune liver disease affecting small bile ducts. Clinicians need accurate long-term prognosis tools, but existing approaches lack interpretability. Black-box models hinder clinical adoption.

## Objectives
1. Develop a validated 5-year severe event predictor for PBC
2. Implement SHAP-based explainability for clinical trust
3. Build user-friendly web interface for clinicians
4. Maintain prediction history with audit capabilities
5. Deploy as accessible web application

## Dataset
- **Source:** Mayo Clinic PBC Trial (1974-1984)
- **Cohort:** 329 patients after filtering for 5-year follow-up
- **Events:** 132 (40.1%) - death or liver transplant within 5 years
- **Censored:** 197 (59.9%) - event-free at 5 years
- **Features (17):** age, sex, ascites, hepatomegaly, spiders, edema, bilirubin, cholesterol, albumin, copper, alk_phos, SGOT, triglicerides, platelets, prothrombin, stage, drug

## Methodology
### Preprocessing
- Missing data imputed with IterativeImputer
- Standardization with StandardScaler (fit only on training folds)
- Stratified 5-fold cross-validation to prevent leakage

### Model Development
Evaluated Logistic Regression, Random Forest, and XGBoost. Logistic Regression selected for:
- Best calibration (Brier Score: 0.1363)
- Excellent discrimination (AUC: 0.8800)
- High interpretability and clinical acceptability
- Fast inference suitable for web deployment

### Explainability
SHAP LinearExplainer provides feature attributions showing how each lab value pushes risk up/down from baseline.

## Model Performance
| Model | ROC-AUC (CV) | Precision | Recall | F1-Score | Brier Score |
|---|---|---|---|---|---|
| Logistic Regression | 0.8800 | 0.7675 | 0.8105 | 0.7861 | 0.1363 |
| Random Forest | 0.8844 | 0.7235 | 0.8256 | 0.7694 | 0.1419 |
| XGBoost | 0.8706 | 0.7225 | 0.7880 | 0.7508 | 0.1528 |

**Out-of-Fold ROC-AUC:** 0.8828 (95% CI: [0.8409, 0.9185])  
**Baseline (class-prior):** ROC-AUC = 0.4924

## Architecture
```
Frontend (Streamlit) --> Backend (FastAPI) --> ML Pipeline (sklearn)
                        |                      --> SHAP Explainer
                        v
                      SQLite DB
```

## Implementation

### Backend (`backend/`)
- `main.py`: FastAPI app with `/predict`, `/health`, `/history`, `/stats` endpoints
- `db.py`: SQLite with WAL mode, indexes, migrations, prediction logging
- `schemas.py`: Pydantic validation models

### Frontend (`frontend/`)
- `app.py`: Streamlit UI with forms, visualizations, history, PDF export
- Risk bands: Low (<0.15), Intermediate (0.15-0.40), High (≥0.40)
- SHAP waterfall plots, feature importance
- CSV/PDF export capabilities

### ML Pipeline
- Training scripts in `ml/`: data prep, training, evaluation
- Artifacts in `models/`: `model.pkl`, `training_metrics.json`
- Validation in `validation/`: calibration plots, reports

## Features
- [x] Risk prediction with 17 clinical features
- [x] SHAP explainability (waterfall + bar charts)
- [x] Risk stratification into bands
- [x] Input validation with clinical ranges
- [x] Prediction history with SQLite persistence
- [x] History filtering by risk band
- [x] CSV export of history
- [x] PDF report generation per prediction
- [x] Backend health monitoring
- [x] Aggregate statistics dashboard
- [x] Model comparison visualization
- [x] Confidence interval display
- [x] Docker containerization
- [x] Cloud deployment (Render + Streamlit Cloud)

## Testing
62+ tests across backend, frontend, and ML components with pytest.

## Deployment
- **Backend:** Deployed on Render at https://hepatiq-ai.onrender.com
- **Frontend:** Deployed on Streamlit Cloud at https://hepatiq-ai.streamlit.app
- **Local:** `docker-compose up` for full stack

## Limitations
- Historical cohort from single center (1974-1984) - may not generalize
- Small sample size (n=329)
- PBC-specific only
- Missing some modern prognostic markers (INR/creatinine for MELD)
- Research tool, not FDA-cleared for clinical decision making
- SQLite storage not suitable for multi-user production at scale

## Future Enhancements
- External validation on contemporary cohorts
- Time-to-event survival modeling (Cox regression, RSF)
- Batch predictions from CSV
- User authentication and role-based access
- Integration with EHR systems (HL7/FHIR)
- Model monitoring and drift detection
- Calibration plots in UI

## Conclusion
HepatiQ demonstrates a complete, explainable ML pipeline from data to deployment. With ROC-AUC ~0.88 and strong interpretability via SHAP, it shows promise as a clinical decision support tool while maintaining transparency about its limitations.

## References
1. Dickson ER, Grambsch PM, Fleming TR, Fisher LD, Langworthy A. Prognosis in primary biliary cirrhosis: model for decision making. Hepatology. 1989;10:1-7.
2. Lundberg SM, Lee SI. A Unified Approach to Interpreting Model Predictions. NeurIPS 2017.
3. Mayo Clinic PBC Dataset - UCI Machine Learning Repository
