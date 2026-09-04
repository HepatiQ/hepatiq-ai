# Getting Started — HepatiQ

Welcome to the HepatiQ team! This guide walks you through setting up the project on your computer and starting work on your assigned module.

HepatiQ is a clinical decision-support system that predicts 5-year severe event risk (death or liver transplant) in Primary Biliary Cholangitis (PBC) patients using machine learning and SHAP explainability. Each team member works on a distinct, modular component.

## Prerequisites

Before you begin, install:
- **Python 3.10+** — [python.org](https://python.org)
- **Git** — [git-scm.com](https://git-scm.com)
- **VS Code** (or your preferred editor) — [code.visualstudio.com](https://code.visualstudio.com)
- A **GitHub account**, added to the `HepatiQ/hepatiq-ai` repository

## Clone the Repository

1. Go to [github.com/HepatiQ/hepatiq-ai](https://github.com/HepatiQ/hepatiq-ai)
2. Click the green **Code** button → copy the HTTPS link
3. Open a terminal and run:
   ```bash
   git clone https://github.com/HepatiQ/hepatiq-ai.git
   cd hepatiq-ai
   ```

## Open the Project in Your Editor

- **File → Open Folder** → select the `hepatiq-ai` folder

## Set Up Python Environment

HepatiQ is a pure-Python project. Create and activate a virtual environment, then install all dependencies:

```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Create Your Own Branch

Never work directly on `main`. Create a feature branch named after yourself and your task:

```bash
git checkout main
git pull origin main
git checkout -b yourname-your-task
```

**Example branch names:**

| Team Member | Branch Example |
|---|---|
| Nirali | `nirali-model-training` |
| Pranjal | `pranjal-backend-api` |
| Deekshitha | `deekshitha-streamlit-ui` |
| Rudra | `rudra-validation-ci` |

## Project Folder Structure

Each team member owns one folder. Keep your code there and coordinate with teammates via pull requests.

| Folder | Owner | Responsibility |
|---|---|---|
| `ml/` | Nirali | Data ingestion, cohort filtering, preprocessing (IterativeImputer, StandardScaler), model training (Logistic Regression + XGBoost), cross-validation, SHAP generation |
| `backend/` | Pranjal | FastAPI application, `/predict` endpoint, Pydantic validation, model loading (joblib), SHAP integration |
| `frontend/` | Deekshitha | Streamlit UI, input forms, risk scorecard rendering, SHAP visualization charts (Plotly) |
| `validation/` | Rudra | Bootstrap confidence intervals, MELD score benchmarking, Brier score, statistical testing, clinical limitations documentation |
| `data/` | Nirali | Raw and preprocessed Mayo Clinic PBC dataset |
| `models/` | Nirali & Pranjal | Trained `.pkl` model files (Logistic Regression + XGBoost pipeline) |
| `docs/` | Everyone | Team documentation, roadmap, workflow guides |

## Running the Project Locally

Start the backend (in one terminal):
```bash
uvicorn backend.main:app --reload
```

The backend will run at `http://localhost:8000`.

Start the frontend (in a separate terminal):
```bash
streamlit run frontend/app.py
```

The frontend will run at `http://localhost:8501`. Open it in your browser.

**No API keys or `.env` file required** — the entire stack runs locally on open-source libraries.

## Commit and Push Your Work

Commit often with clear, descriptive messages:

```bash
git add .
git commit -m "Add SHAP waterfall chart to results page"
git push
```

**First push tip:** Git may ask you to set the upstream branch. Copy-paste the command it suggests:
```bash
git push --set-upstream origin yourname-your-task
```

## Open a Pull Request

1. Go to [github.com/HepatiQ/hepatiq-ai](https://github.com/HepatiQ/hepatiq-ai)
2. You'll see a banner prompting you to create a pull request for your branch
3. Click **Compare & pull request**
4. Write a clear title and description of what you changed
5. Request review from a teammate
6. Once approved (and CI passes if configured), merge into `main`

## Workflow Summary

```
main (stable)
    └──→ yourname-your-task (your feature branch)
            └──→ commit, commit, commit
            └──→ push
            └──→ open PR
            └──→ team review
            └──→ merge to main
            └──→ delete branch
```
