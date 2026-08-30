# Getting Started — HepatiQ

Welcome to the team! This guide walks you through setting up the project on your computer and starting work on your module.

## 1. Prerequisites

Before you begin, make sure you have installed:
- **Python 3.10+** — [python.org](https://python.org)
- **Git** — [git-scm.com](https://git-scm.com)
- **VS Code** — [code.visualstudio.com](https://code.visualstudio.com)
- A **GitHub account**, added to the `hepatiq-ai` repository

## 2. Clone the repository

1. Go to `github.com/<your-org-or-username>/hepatiq-ai`
2. Click the green **Code** button → copy the HTTPS link
3. Open a terminal on your computer and run:
   ```bash
   git clone https://github.com/<your-org-or-username>/hepatiq-ai.git
   ```

## 3. Open the project in VS Code

- **File → Open Folder** → select the `hepatiq-ai` folder that was just created

## 4. Set up your Python environment

HepatiQ is a pure-Python project — everyone works from the same virtual environment, so there's no separate mobile/web toolchain to install.

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 5. Create your own branch

Never work directly on `main`. Create a branch named `yourname/short-description`:

```bash
git checkout main
git pull
git checkout -b yourname/what-youre-building
```

**Example branch names:**

| Member | Branch |
|---|---|
| Nirali | `nirali/model-training` |
| Pranjal | `pranjal/backend-api` |
| Deekshitha | `deekshitha/streamlit-ui` |
| Rudra | `rudra/validation` |

## 6. Project folder structure

Work inside your assigned folder:

| Folder | Owner | What goes here |
|---|---|---|
| `ml/` | Nirali | Data cleaning, imputation, model training, SHAP generation |
| `backend/` | Pranjal | FastAPI app, endpoints, model loading |
| `frontend/` | Deekshitha | Streamlit UI, input forms, chart rendering |
| `validation/` | Rudra | Statistical tests, MELD benchmarking, confidence intervals |
| `data/` | Nirali | Raw and cleaned dataset |
| `models/` | Nirali / Pranjal | Trained `.pkl` model files |
| `docs/` | Everyone | Documentation — each person's section in their own file |

## 7. Running the project locally

Start the backend:
```bash
uvicorn backend.main:app --reload
```

Start the frontend, in a separate terminal:
```bash
streamlit run frontend/app.py
```

By default the backend runs at `http://localhost:8000` and the frontend at `http://localhost:8501`. No API keys or `.env` file are required — the whole stack runs locally on open-source librarie[...]

## 8. Save your work

Commit often, with clear messages describing what changed:

```bash
git add .
git commit -m "add SHAP waterfall chart to results page"
git push
```

First time pushing a new branch, Git may ask you to run:
```bash
git push --set-upstream origin yourname/your-branch
```
Just copy-paste that exact line if it appears.

## 9. Open a Pull Request

1. Go to the `hepatiq-ai` repository on GitHub
2. You'll see a banner for your recently pushed branch → click **Compare & pull request**
3. Give it a clear title, then **Create pull request**
4. Once reviewed (or if it's routine setup work), merge it into `main`

## 10. Task tracking

Check the **Issues** tab for your assigned checklist of tasks. Move your card across the **Project board** (To Do → In Progress → In Review → Done) as you make progress.

## Questions?

Ask in the team group chat, or tag a teammate directly on your Pull Request or Issue.
