# HepatiQ Documentation

Start here. Docs are grouped by audience and intent.

## Getting started

- [GETTING_STARTED.md](GETTING_STARTED.md) — clone, install, run backend + frontend
- [DEMO.md](DEMO.md) — scripted demo flow and safe claims
- [TEAM_WORKFLOW.md](TEAM_WORKFLOW.md) — branching, PRs, review

## Outreach & reproducibility

- [outreach/POSITIONING.md](outreach/POSITIONING.md) — positioning and claims guardrails
- [outreach/TECHNICAL_NOTE.md](outreach/TECHNICAL_NOTE.md) — full technical note
- [outreach/EVIDENCE_BRIEF.md](outreach/EVIDENCE_BRIEF.md) — one-page evidence brief
- [outreach/CONFERENCE.md](outreach/CONFERENCE.md) — abstract and poster outline
- [../video_demo.mp4](../video_demo.mp4) — recorded demo video
- [outreach/DEMO_VIDEO_SCRIPT.md](outreach/DEMO_VIDEO_SCRIPT.md) — two-minute recording script
- [outreach/LAUNCH_COPY.md](outreach/LAUNCH_COPY.md) — release and social copy
- [../notebooks/hepatiq_reproducibility.ipynb](../notebooks/hepatiq_reproducibility.ipynb) — validation and benchmark regeneration

## Model & evidence

- [model_card.md](model_card.md) — intended use, training data, metrics, ethics
- [MODEL_COMPARISON.md](MODEL_COMPARISON.md) — LR vs RF vs XGBoost
- [LIMITATIONS.md](LIMITATIONS.md) — what the evidence does and does not support
- [ROADMAP.md](ROADMAP.md) — phase history and decisions

## Planning & status

- [IMPROVEMENT_ROADMAP.md](IMPROVEMENT_ROADMAP.md) — prioritized remaining work and execution plan
- [NEXT_STEPS.md](NEXT_STEPS.md) — historical Phase 5 handoff notes; see the roadmap for current status
- [reports/PROJECT_REPORT.md](reports/PROJECT_REPORT.md) — full project report
- [reports/WEEK_BY_WEEK_PROGRESS.md](reports/WEEK_BY_WEEK_PROGRESS.md) — weekly progress log

## Onboarding

- [../onboarding/DEEKSHITHA_FRONTEND_DEVELOPER.md](../onboarding/DEEKSHITHA_FRONTEND_DEVELOPER.md)
- [../onboarding/NIRALI_ML_ENGINEER.md](../onboarding/NIRALI_ML_ENGINEER.md)
- [../onboarding/RUDRA_VALIDATION_ENGINEER.md](../onboarding/RUDRA_VALIDATION_ENGINEER.md)

## Code layout

```text
src/hepatiq/
  backend/     FastAPI service (/predict, /predict/batch)
  frontend/    Streamlit UI, bulk CSV view, pages/
  ml/          training, cohort building, SHAP
  validation/  OOF validation + report
  paths.py     shared path constants
data/          external canonical exports, archived raw, processed / interim
models/        model.skops + candidates/
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
