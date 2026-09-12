#!/usr/bin/env python3
"""
Script to create HepatiQ project issues using the GitHub API.
Run: python create_issues.py

Before running:
1. Replace GITHUB_TOKEN below with a real GitHub Personal Access Token
   (Settings -> Developer settings -> Personal access tokens -> generate one
   with "repo" scope, or fine-grained access to Issues on HepatiQ/hepatiq-ai).
2. Never commit your real token -- keep it out of the file you push. Consider
   reading it from an environment variable instead:
       GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
"""

import requests
from typing import Optional

GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"  # Replace with your token
REPO = "HepatiQ/hepatiq-ai"
API_URL = "https://api.github.com"

issues_data = [
    # ---------------- Milestone 1 — Connect Trained Model to App ----------------
    {
        "title": "Replace placeholder 5-feature input with full 17-feature clinical form",
        "body": """## Objective
The deployed frontend (`frontend/app.py`) still collects only the old 5-biomarker
placeholder set (Bilirubin, Albumin, Age, Prothrombin Time, Platelets). The real
trained model (`models/model.pkl`) requires all 17 Mayo PBC features. Update the
Streamlit form to collect all 17.

## Key Tasks
- [ ] Add form inputs for all 17 features (see `models/training_metrics.json`
      -> `feature_columns` for the exact list and order)
- [ ] Numeric validation on all numeric fields
- [ ] Sensible default values / handling for fields a user leaves blank
- [ ] Field names/order match `impute_pipeline.py::build_feature_frame` exactly

## Acceptance Criteria
- All 17 variables present in the form
- Validation on numeric fields
- Missing values handled without crashing
- Input names match the training pipeline exactly (case-sensitive: `alk.phos`, etc.)

## Related Components
- `frontend/app.py`
- `ml/impute_pipeline.py` (feature list source of truth)

## Priority
High""",
        "assignees": [""],
        "labels": ["@Deekshitha-Frontend", "@Pranjal-Backend", "feature", "high-priority"],
    },
    {
        "title": "Update FastAPI prediction schema to 17 features",
        "body": """## Objective
`backend/main.py`'s `PredictRequest` Pydantic model still hardcodes the old
5-feature schema and will throw a shape-mismatch error against the real
17-feature `models/model.pkl`. Align the backend with the actual trained model.

## Key Tasks
- [ ] Update `PredictRequest` to accept all 17 features, matching
      `ml/impute_pipeline.py::build_feature_frame` field names and order
- [ ] Update the `/predict` handler to build the feature array/DataFrame in
      the correct column order before calling `model.predict_proba(...)`
- [ ] Update or remove the SHAP explainer call in `backend/main.py` to use
      `shap.LinearExplainer`, matching the final model (Logistic Regression,
      see Issue #11)
- [ ] Update API docs / OpenAPI schema (FastAPI auto-generates this from the
      Pydantic model, but double check descriptions are accurate)

## Acceptance Criteria
- Pydantic schema updated to 17 fields
- `/predict` accepts all 17 features and returns a valid probability
- Successful inference using the real `models/model.pkl`, not the old
  placeholder
- No shape-mismatch errors

## Related Components
- `backend/main.py`
- `models/model.pkl`

## Priority
High""",
        "assignees": [""],
        "labels": ["@Pranjal-Backend", "feature", "high-priority"],
    },
    {
        "title": "End-to-end prediction testing (Streamlit -> FastAPI -> Model -> SHAP)",
        "body": """## Objective
Verify the full request path works after Issues #1 and #2 land: a user fills
out the Streamlit form, the request reaches FastAPI, the model scores it, and
a SHAP explanation is returned and displayed.

## Key Tasks
- [ ] Manually test with at least one known patient record (compare against
      `ml/explain.py`'s output for the same patient as a ground truth check)
- [ ] Test edge cases: missing optional fields, boundary values (age=0,
      very high bilirubin, etc.)
- [ ] Confirm SHAP explanation values match what `ml/explain.py` produces
      for the same input, so backend and offline explainability don't drift

## Acceptance Criteria
- A test patient is successfully scored end-to-end
- Risk probability displayed correctly in the UI
- SHAP explanation displayed and matches `ml/explain.py`'s output for the
  same patient
- No backend errors across the tested cases

## Related Components
- `frontend/app.py`, `backend/main.py`, `ml/explain.py`

## Priority
High""",
        "assignees": [""],
        "labels": ["@Pranjal-Backend", "testing", "high-priority"],
    },
    # ---------------- Milestone 2 — Explainability ----------------
    {
        "title": "Integrate SHAP visualization into the Streamlit dashboard",
        "body": """## Objective
Display the per-patient SHAP explanation directly in the Streamlit UI,
building on the working console version in `ml/explain.py`.

## Key Tasks
- [ ] Reuse `ml/explain.py`'s logic (or the backend's SHAP call from
      Issue #2) to get per-feature impact values for the submitted patient
- [ ] Render a waterfall or bar chart (Plotly, per the team's existing
      preference over matplotlib) showing each feature's contribution
- [ ] Show a feature-contribution table alongside the chart
- [ ] Clearly mark positive (risk-increasing) vs negative (risk-decreasing)
      contributors

## Acceptance Criteria
- Waterfall or bar chart visible in the dashboard
- Feature contribution table visible
- Positive/negative contributors visually distinguished

## Related Components
- `frontend/app.py`
- `ml/explain.py`

## Priority
High""",
        "assignees": [""],
        "labels": ["@Deekshitha-Frontend", "feature", "high-priority"],
    },
    {
        "title": "Add a plain-language clinical interpretation panel",
        "body": """## Objective
Auto-generate a short, human-readable sentence summarizing the SHAP result,
so a clinician doesn't have to read a raw feature-impact table to get the
gist.

Example: "Elevated bilirubin and low albumin increased risk. Higher platelet
count reduced risk."

## Key Tasks
- [ ] Take the top N SHAP contributors (positive and negative) for a patient
- [ ] Map feature names to clinician-friendly phrasing (e.g. `bili` ->
      "bilirubin", `alk.phos` -> "alkaline phosphatase")
- [ ] Generate a 1-2 sentence auto-summary from the top contributors

## Acceptance Criteria
- Auto-generated interpretation sentence displayed
- Based on the actual top SHAP features for that patient, not hardcoded text

## Related Components
- `frontend/app.py`

## Priority
Medium""",
        "assignees": [""],
        "labels": ["@Pranjal-Backend", "feature", "medium-priority"],
    },
    # ---------------- Milestone 3 — Validation & Research ----------------
    {
        "title": "Generate a reliability (calibration) diagram for the final model",
        "body": """## Objective
The model card currently reports Brier score but not a full calibration
curve. Add one to visually confirm how well-calibrated the deployed model's
probabilities actually are.

## Key Tasks
- [ ] Use `sklearn.calibration.calibration_curve` (or similar) on
      cross-validated out-of-fold predictions
- [ ] Plot predicted probability vs. observed frequency
- [ ] Save the figure under `validation/`
- [ ] Reference it from `docs/model_card.md`

## Acceptance Criteria
- Reliability plot created and saved under `validation/`
- Plot referenced in the model card / report

## Related Components
- `validation/validate.py`
- `docs/model_card.md`

## Priority
High""",
        "assignees": [""],
        "labels": ["@Rudra-Validation", "research", "high-priority"],
    },
    {
        "title": "Add bootstrap confidence intervals alongside CV metrics",
        "body": """## Objective
Cross-validation CIs (t-distribution, n=5 folds) are already in
`models/training_metrics.json`, but a bootstrap-based estimate would give a
second, less-assumption-heavy uncertainty estimate on the final model's
predictions -- useful for the report given how much weight the CI-overlap
question has carried in model selection.

## Key Tasks
- [ ] Use `validation/validate.py::bootstrap_ci` (already implemented) on
      the final model's out-of-sample predictions
- [ ] Run at least 1000 bootstrap resamples
- [ ] Report bootstrap CIs for ROC-AUC and Brier score
- [ ] Compare against the existing CV-fold-based CIs -- note whether they
      broadly agree or disagree

## Acceptance Criteria
- 1000+ bootstrap iterations run
- ROC-AUC bootstrap CI reported
- Brier score bootstrap CI reported

## Related Components
- `validation/validate.py`

## Priority
Medium""",
        "assignees": [""],
        "labels": ["@Rudra-Validation", "research", "medium-priority"],
    },
    {
        "title": "Benchmark HepatiQ against the Mayo Risk Score",
        "body": """## Objective
`validation/validate.py::compare_to_meld` is currently a stub. Implement a
real comparison against a classical PBC prognostic tool so the report can
say something evidence-based about how HepatiQ compares to existing clinical
scores, not just to itself.

## Key Tasks
- [ ] Implement the Mayo Risk Score formula for PBC (not MELD -- MELD is a
      general end-stage liver disease score; Mayo's own PBC-specific score
      is the more appropriate comparator here and what the dataset was
      originally used to validate)
- [ ] Compute Mayo Risk Score for the same 329-patient cohort
- [ ] Compare discrimination (ROC-AUC) and calibration side by side
- [ ] Document the comparison, including where HepatiQ over- or
      under-performs the classical score, and why that might be

## Acceptance Criteria
- Mayo Risk Score implemented and computed on the cohort
- Performance comparison table (HepatiQ vs. Mayo Risk Score)
- Discussion of results added to documentation

## Related Components
- `validation/validate.py`
- `docs/model_card.md`

## Priority
High""",
        "assignees": [""],
        "labels": ["@Nirali-ML", "@Rudra-Validation", "research", "high-priority"],
    },
    # ---------------- Milestone 4 — Product Quality ----------------
    {
        "title": "Prediction history dashboard (SQLite)",
        "body": """## Objective
Log each prediction to SQLite (per the project's established no-JWT,
SQLite-only session logging scope) and surface a simple history view.

## Key Tasks
- [ ] Log patient input, risk score, and timestamp to SQLite on each
      `/predict` call
- [ ] Build a Streamlit table view of past predictions
- [ ] Add basic search
- [ ] Add sort-by-date

## Acceptance Criteria
- Table view of prediction history
- Search functionality
- Sortable by date

## Related Components
- `backend/main.py`
- `frontend/app.py`

## Priority
Medium""",
        "assignees": [""],
        "labels": ["@Deekshitha-Frontend", "feature", "medium-priority"],
    },
    {
        "title": "Export risk report as PDF",
        "body": """## Objective
Let a clinician download a patient's risk assessment (score + SHAP
explanation) as a PDF for their records.

## Key Tasks
- [ ] Generate a PDF containing: risk score, SHAP explanation, timestamp
- [ ] Add a download button in the Streamlit UI

## Acceptance Criteria
- PDF includes risk score, SHAP explanation, and timestamp
- Downloadable from the UI

## Related Components
- `frontend/app.py`

## Priority
Medium""",
        "assignees": [""],
        "labels": ["@Pranjal-Backend", "feature", "medium-priority"],
    },
    # ---------------- Milestone 5 — Documentation ----------------
    {
        "title": "Document the model-selection decision: Logistic Regression over Random Forest",
        "body": """## Objective
Cross-validation shows Logistic Regression and Random Forest are NOT
statistically distinguishable on this cohort -- their 95% CIs overlap on
every metric (ROC-AUC, precision, recall, F1, Brier). Random Forest has a
marginally higher point-estimate ROC-AUC, but Logistic Regression has been
selected as the final model, on the following principle: since HepatiQ
outputs a continuous risk *probability* rather than a fixed-threshold
decision, calibration (Brier score) is prioritized over recall as the
tie-breaker in `ml/train.py::select_winner`. Logistic Regression has the
best calibration of the three candidates (Brier 0.1363 vs. Random Forest's
0.1419), which is why it wins under that rule.

## Key Tasks
- [ ] Update `docs/model_card.md` and `README.md` to state the CI-overlap
      finding explicitly (LR and RF are not statistically distinguishable),
      not just report LR as if it were a decisive, uncontested winner
- [ ] Document the calibration-first tie-break principle and why it applies
      to a risk-score tool specifically
- [ ] Leave `ml/train.py::select_winner`'s tie-break order (Brier before
      Recall) as-is going forward -- do not reorder it again based on which
      model it happens to produce

## Acceptance Criteria
- Tie-break principle (calibration over recall) documented with reasoning,
  not just an outcome
- CI-overlap between LR and RF explicitly discussed in the model card, not
  glossed over
- `docs/model_card.md` updated and linked from `README.md`

## Related Components
- `ml/train.py`, `docs/model_card.md`, `README.md`

## Priority
High""",
        "assignees": [""],
        "labels": ["@Pranjal-Backend", "documentation", "high-priority"],
    },
    {
        "title": "Create a system architecture diagram",
        "body": """## Objective
A single professional architecture figure for the README and viva
presentation, showing how the pieces fit together.

## Key Tasks
- [ ] Diagram covering: Streamlit frontend -> FastAPI backend -> trained
      model (Logistic Regression) -> SHAP explainer -> SQLite logging
- [ ] Add to `README.md`
- [ ] Add to presentation materials

## Acceptance Criteria
- Diagram includes Streamlit, FastAPI, the final model, SHAP, and SQLite
- Added to README and presentation deck

## Related Components
- `README.md`

## Priority
Medium""",
        "assignees": [""],
        "labels": ["@Pranjal-Backend", "@Nirali-ML", "@Deekshitha-Frontend", "@Rudra-Validation", "documentation", "medium-priority"],
    },
    # ---------------- Stretch Goals ----------------
    {
        "title": "[Stretch] Docker deployment",
        "body": "Containerize the FastAPI backend and Streamlit frontend for reproducible local/cloud deployment. Not required for the academic submission; consider only after Milestones 1-5 are complete.",
        "assignees": [""],
        "labels": ["@Pranjal-Backend", "stretch-goal"],
    },
    {
        "title": "[Stretch] CI/CD with GitHub Actions",
        "body": "Add a GitHub Actions workflow to run `ml/train.py` reproducibility checks and/or basic backend tests on each PR.",
        "assignees": [""],
        "labels": ["@Pranjal-Backend", "stretch-goal"],
    },
    {
        "title": "[Stretch] User authentication",
        "body": "Out of current scope per project decisions (no JWT auth planned). Revisit only if the project scope expands beyond the academic submission.",
        "assignees": [""],
        "labels": ["stretch-goal"],
    },
    {
        "title": "[Stretch] External validation dataset",
        "body": "Validate the model against a PBC cohort outside the Mayo trial data, if one becomes available, to test generalization beyond this specific historical cohort.",
        "assignees": [""],
        "labels": ["@Nirali-ML", "@Rudra-Validation", "stretch-goal"],
    },
    {
        "title": "[Stretch] Risk stratification categories (Low / Moderate / High)",
        "body": "Bucket the continuous risk score into Low/Moderate/High risk categories with clinically justified thresholds, for easier at-a-glance interpretation.",
        "assignees": [""],
        "labels": ["@Nirali-ML", "stretch-goal"],
    },
    {
        "title": "[Stretch] Compare against GLOBE score",
        "body": "Add the GLOBE score as a second classical-score comparator alongside the Mayo Risk Score (Issue #8).",
        "assignees": [""],
        "labels": ["@Nirali-ML", "@Rudra-Validation", "stretch-goal"],
    },
    {
        "title": "[Stretch] Compare against UK-PBC score",
        "body": "Add the UK-PBC score as a third classical-score comparator alongside Mayo Risk Score and GLOBE score.",
        "assignees": [""],
        "labels": ["@Nirali-ML", "@Rudra-Validation", "stretch-goal"],
    },
    {
        "title": "[Stretch] Deploy a public demo",
        "body": "Deploy the app publicly (e.g. Streamlit Community Cloud or similar) for portfolio/demo purposes, after Docker/CI work is done.",
        "assignees": [""],
        "labels": ["@Pranjal-Backend", "stretch-goal"],
    },
]


def create_issue(title: str, body: str, labels: list, assignees: Optional[list] = None) -> dict:
    """Create a single issue in the repository"""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    payload = {
        "title": title,
        "body": body,
        "labels": labels,
    }

    if assignees and assignees[0]:
        payload["assignees"] = assignees

    url = f"{API_URL}/repos/{REPO}/issues"
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 201:
        return {"success": True, "issue": response.json()}
    else:
        return {"success": False, "error": response.json()}


def main():
    print(f"Creating {len(issues_data)} issues in {REPO}...\n")

    for i, issue in enumerate(issues_data, 1):
        result = create_issue(
            title=issue["title"],
            body=issue["body"],
            labels=issue["labels"],
            assignees=issue["assignees"],
        )

        if result["success"]:
            issue_num = result["issue"]["number"]
            print(f"\u2705 #{issue_num}: {issue['title']}")
        else:
            print(f"\u274c Failed: {issue['title']}")
            print(f"   Error: {result['error']}")

    print(f"\nDone! Visit: https://github.com/{REPO}/issues")


if __name__ == "__main__":
    main()