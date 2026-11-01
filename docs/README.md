# HepatiQ Documentation

Start here. Docs are grouped by audience and intent.

## Getting started

- [GETTING_STARTED.md](GETTING_STARTED.md) — clone, install, run backend + frontend
- [DEMO.md](DEMO.md) — scripted demo flow and safe claims
- [TEAM_WORKFLOW.md](TEAM_WORKFLOW.md) — branching, PRs, review

## Model & evidence

- [model_card.md](model_card.md) — intended use, training data, metrics, ethics
- [MODEL_COMPARISON.md](MODEL_COMPARISON.md) — LR vs RF vs XGBoost
- [LIMITATIONS.md](LIMITATIONS.md) — what the evidence does and does not support
- [ROADMAP.md](ROADMAP.md) — phase history and decisions

## Planning & status

- [IMPROVEMENT_ROADMAP.md](IMPROVEMENT_ROADMAP.md) — prioritized remaining work and execution plan
- [NEXT_STEPS.md](NEXT_STEPS.md) — earlier handoff notes (partially stale after P0)
- [reports/PROJECT_REPORT.md](reports/PROJECT_REPORT.md) — full project report
- [reports/WEEK_BY_WEEK_PROGRESS.md](reports/WEEK_BY_WEEK_PROGRESS.md) — weekly progress log

## Onboarding

- [../onboarding/DEEKSHITHA_FRONTEND_DEVELOPER.md](../onboarding/DEEKSHITHA_FRONTEND_DEVELOPER.md)
- [../onboarding/NIRALI_ML_ENGINEER.md](../onboarding/NIRALI_ML_ENGINEER.md)
- [../onboarding/RUDRA_VALIDATION_ENGINEER.md](../onboarding/RUDRA_VALIDATION_ENGINEER.md)

## Code layout

```text
src/hepatiq/
  backend/     FastAPI service
  frontend/    Streamlit UI
  ml/          training, cohort building, SHAP
  validation/  OOF validation + report
  paths.py     shared path constants
data/          raw / processed / interim datasets
models/        model.pkl + candidates/
tests/         pytest suite
```

Setup and run commands:

```bash
pip install -r requirements.txt
pip install -e . --no-deps
uvicorn hepatiq.backend.main:app --reload
streamlit run src/hepatiq/frontend/app.py
python -m pytest
```
