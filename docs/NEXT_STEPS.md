# Next Steps & Open Items

Handoff notes for whoever picks this project up next (human teammate or a fresh
AI session). Everything shipped is committed on `main`; this file captures the
*informal* context that isn't obvious from the code — what's deliberately not
done, what was deferred, and known issues.

Last updated alongside commit `714f6e3` (Phase 5 delivery). Status: all CI green,
62 tests passing, ~63% coverage gate.

## Where the project stands

The application is complete and honest as a **research prototype**:

- Model: Logistic Regression, leakage-controlled 5-fold CV, OOF ROC-AUC
  **0.8828 [0.8409, 0.9185]** vs class-prior baseline 0.4924 (`validation/report.md`).
- Backend: FastAPI (`backend/main.py`) — `/health`, `/predict`, `GET /history`, `DELETE /history`.
- Frontend: Streamlit (`frontend/app.py`) — dark theme, logo, risk-band badge,
  training-range warnings, latency/version caption, history controls.
- Quality: 62 tests incl. a live form→API→model E2E, ruff clean, CI coverage floor 60.
- Docs: `README.md`, `docs/LIMITATIONS.md`, `docs/model_card.md`, `docs/DEMO.md`,
  `docs/ROADMAP.md` (Phases 4 & 5 marked complete).

## Highest-value next step: external validation

**This is the single biggest lever for making the project "more useful."** Right
now all numbers come from one 1974–1984 Mayo cohort; performance elsewhere is
unproven. External validation on a second PBC cohort would turn "promising on one
dataset" into evidence of generalization.

Options, in order of honesty/value:

- **Option A — true external validation (best).** Score the frozen
  `models/model.pkl` on a dataset it has *never* seen with the same features and
  an outcome column. Candidate cohorts: UK-PBC, GLOBAL PBC / GLOBE, or the
  Mayo/VA cohorts (the latter also carry creatinine + INR, which would finally
  enable a real MELD benchmark — see `docs/LIMITATIONS.md`).
  - **What to build when a cohort exists:** `validation/run_external_validation.py`
    that loads the frozen model, scores the new cohort, reports ROC-AUC / Brier /
    calibration with 95% bootstrap CIs vs a class-prior baseline, and writes
    `validation/external_report.md`. Label it clearly as *external* (not OOF).
  - **Blocker:** requires data access. Nothing to code until a second dataset is
    in hand.
- **Option B — held-out test (bridge, weaker).** Deterministic 80/20 stratified
  hold-out of the existing 329 patients; train a fresh pipeline on 80%, score the
  untouched 20%. Honest but **must be labeled "held-out," not "external."** ~1 hour.
- **Option C — synthetic cross-cohort check.** Do **not** dress this up as
  external validation; it is not.

## Deferred (optional, none blocking)

- **API key + rate limiting.** `docs/LIMITATIONS.md` states neither exists. Only
  matters if the Render URL is shared publicly. ~2 hours. Suggest `X-API-Key` via
  env + a simple in-memory limiter, with 401/429 tests.
- **Bulk CSV scoring.** `POST /predict/batch` (≤1000 rows) + upload UI → scored
  table + downloadable CSV. Turns the product from "calculator" to "cohort tool."
  ~half a day incl. tests. Nice-to-have, not a correctness gap.
- **README screenshot.** A UI screenshot near the top showcases the dark theme to
  reviewers/graders.
- **`docs/model_card.md`** doesn't repeat the OOF AUC confidence interval that
  the rest of the docs cite. Minor consistency fix.
- **Render persistence.** `data/hepatiq.db` lives on ephemeral disk and resets per
  deploy. Documented; only fix if history must survive restarts (attach a disk +
  set `HEPATIQ_DB_PATH`). Blueprint comments in `render.yaml` show how.

## Known issues / cautions

- **Leaked GitHub PAT (unresolved, likely moot).** `create_issues.py` (line ~18)
  contained a hardcoded `ghp_…` token. It is tracked in git history. It now
  returns **HTTP 401** (revoked/expired), so the credential is dead — but the file
  still contains the string. If it was never revoked, **revoke it** at
  github.com/settings/tokens, then remove the file. A secret-scan step in CI would
  prevent recurrence.
- **Dependency pins are deliberate.** `requirements.txt` pins exact versions
  (e.g. `streamlit==1.62.0`). Reason: an unpinned install once pulled a newer
  Streamlit whose form-widget behaviour differed from what the tests were written
  against (an `increment()` regression caught in CI). Do not blanket-unpin.
- **CI Python is 3.12; local dev was 3.14.** Pins were verified to install on
  both. If a future pin isn't available for 3.12, relax only that package to a
  `>=` floor.
- **`data/hepatiq.db`** is gitignored and disposable; the E2E clear-history test
  wipes it. Never commit prediction logs.
- **Not a medical device.** Not FDA/CDSCO-approved, not clinically validated. Keep
  the disclaimer footer and `docs/LIMITATIONS.md` accurate.

## How to run (quick reference)

```bash
# restores to the pinned environment
pip install -r requirements.txt

# API
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# UI
python -m streamlit run frontend/app.py --server.port 8501 --server.headless true
# open http://localhost:8501  ·  API docs: http://localhost:8000/docs

# tests (CI-equivalent)
python -m pytest --cov=backend --cov=ml --cov=validation --cov-fail-under=60
```

Deployment: Render (backend) and Streamlit Cloud (UI) auto-redeploy from `main`.
Streamlit Cloud needs `HEPATIQ_BACKEND_URL` set in app **Secrets** to the Render
service URL; otherwise the UI calls `localhost` and fails.
