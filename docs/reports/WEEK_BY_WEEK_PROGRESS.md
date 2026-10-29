# HepatiQ - Week by Week Progress Report

## Project Timeline: August 30, 2026 - September 6, 2026

### Week 1 (Aug 30 - Sep 5, 2026) - Project Initiation & Setup
**Focus:** Foundation, Team Setup, Project Structure

#### Activities Done:
- Aug 30 - Project initialization and repository setup
- Aug 30 - Team setup: Nirali Verma (Data & ML), Pranjal Dubey (Backend & MLOps), Subbannagari Deekshitha (Frontend UI), Rudra Singh Tomar (Clinical Validation)
- Aug 30 - Created project structure (backend/, frontend/, ml/, models/, data/, validation/, docs/)
- Aug 30 - Documentation setup (README, GETTING_STARTED, TEAM_WORKFLOW, ROADMAP)
- Aug 30 - Normalized repository names and team member details
- Sep 1 - Created GitHub issues for task tracking
- Sep 1 - Added onboarding guides for all team members

**Modules Used:** Git, GitHub, Markdown Documentation  
**Milestone:** Project scaffold complete with team roles defined

### Week 2 (Sep 1 - Sep 6, 2026) - Data, ML & Model Development
**Focus:** Dataset, Preprocessing, Model Training, Integration

#### Activities Done:
- Sep 4 - Added Mayo Clinic PBC dataset
- Sep 4 - Created 5-year severe event target construction script
- Sep 4 - Added imputation and scaling pipeline (IterativeImputer + StandardScaler)
- Sep 5 - Trained and evaluated LR, RF, and XGBoost models
- Sep 5 - Model comparison and selection - Logistic Regression chosen
- Sep 6 - Added model card and updated documentation

**Modules Used:** pandas, numpy, scikit-learn, xgboost, imputation pipelines, cross-validation  
**Milestone:** ML model trained, validated, and documented

### Week 3 (Sep 6 onwards) - Backend, Frontend & Deployment
**Focus:** API Development, UI, Explainability, Deployment

#### Activities Done:
- Backend: FastAPI app with /predict, /health, /history, /stats endpoints
- Frontend: Streamlit UI with forms, SHAP visualizations, history tracking
- Explainability: SHAP LinearExplainer integration
- Database: SQLite with WAL mode, indexes, migrations
- Features: Risk bands, CSV export, PDF report generation, model comparison
- Validation: Confidence intervals, OOF validation, calibration plots
- Deployment: Render (backend), Streamlit Cloud (frontend)
- Containerization: Docker and docker-compose
- Testing: 62+ tests

**Modules Used:** FastAPI, uvicorn, Streamlit, plotly, SHAP, requests, fpdf2, sqlite3, pytest, Docker  
**Milestone:** Full-stack application deployed

## Key Technologies & Tools
| Category | Tools/Libraries |
|---|---|
| Version Control | Git, GitHub |
| Data Processing | pandas, numpy |
| ML | scikit-learn, xgboost, joblib |
| Explainability | SHAP |
| Backend | FastAPI, Pydantic, uvicorn |
| Frontend | Streamlit, Plotly |
| Database | SQLite |
| Testing | pytest |
| Deployment | Render, Streamlit Cloud, Docker |

## Summary
Progressed from setup through ML development, backend/frontend integration, explainability, testing, and deployment. Core features including prediction, SHAP explanations, history tracking, PDF export, and cloud deployment completed.
