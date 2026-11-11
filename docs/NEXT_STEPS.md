# Next Steps & Open Items

> Forward planning now lives in [`IMPROVEMENT_ROADMAP.md`](IMPROVEMENT_ROADMAP.md).
> The status details below predate the P0 remediation and are kept as handoff context.

Handoff notes for whoever picks this project up next (human teammate or a fresh
AI session). Everything shipped is committed on `main`; this file captures the
*informal* context that isn't obvious from the code — what's deliberately not
done, what was deferred, and known issues.

Last updated at Phase 5 delivery. This file is retained as historical handoff
context; [`IMPROVEMENT_ROADMAP.md`](IMPROVEMENT_ROADMAP.md) is now the canonical
status and task tracker.

> **Current update (2026-11-11).** V1 remains the serving model. The v2 survival
> cohort and research-only Cox baseline are on `docs/v2-research-status`, not in
> the serving path. The Cox model did not clear its promotion bar (OOF C-index
> 0.809 vs v1 0.800; delta +0.009 vs required +0.02). The 254-patient landmark
> cohort exists, but no landmark model is implemented. There is no external
> validation; synthetic data is not external validation.

## Where the project stands

The application is complete and honest as a **research prototype**:

- Model: Logistic Regression, leakage-controlled 5-fold CV, OOF ROC-AUC
  **0.8828 [0.8409, 0.9185]** vs class-prior baseline 0.4924 (`src/hepatiq/validation/report.md`).
- Data: canonical 418-row `survival::pbc` (`data/external/pbc.csv`) with pinned
  SHA-256 provenance; the 419-row raw copy is archived, not used for training.
- Backend: FastAPI (`src/hepatiq/backend/main.py`) — `/health`, `/predict`, `GET /history`, `DELETE /history`.
- Frontend: Streamlit (`src/hepatiq/frontend/app.py`) — dark theme, logo, risk-band badge,
  training-range warnings, latency/version caption, history controls.
- Quality: full pytest suite incl. a live form→API→model E2E, ruff clean, CI coverage floor 60.
- Docs: `README.md`, `docs/LIMITATIONS.md`, `docs/model_card.md`, `docs/DEMO.md`,
  `docs/ROADMAP.md` (Phases 4 & 5 marked complete).

## Highest-value next step: external validation

**This is the single biggest lever for making the project "more useful."** Right
now all numbers come from one 1974–1984 Mayo cohort; performance elsewhere is
unproven. External validation on a second PBC cohort would turn "promising on one
dataset" into evidence of generalization.

Options, in order of honesty/value:

- **Option A — true external validation (best).** Score the frozen
  `models/model.skops` pipeline on a dataset it has *never* seen with the same features and
  an outcome column. Candidate cohorts: UK-PBC, GLOBAL PBC / GLOBE, or the
  Mayo/VA cohorts (the latter also carry creatinine + INR, which would finally
  enable a real MELD benchmark — see `docs/LIMITATIONS.md`).
  - **What to build when a cohort exists:** `src/hepatiq/validation/run_external_validation.py`
    that loads the frozen model, scores the new cohort, reports ROC-AUC / Brier /
    calibration with 95% bootstrap CIs vs a class-prior baseline, and writes
    `src/hepatiq/validation/external_report.md`. Label it clearly as *external* (not OOF).
  - **Blocker:** requires data access. Nothing to code until a second dataset is
    in hand.
- **Option B — held-out test (bridge, weaker).** Deterministic 80/20 stratified
  hold-out of the existing 329 patients; train a fresh pipeline on 80%, score the
  untouched 20%. Honest but **must be labeled "held-out," not "external."**
  A related 312-derivation / 106-non-randomized bridge has since been executed
  in the research audit; see `docs/SCORE_BENCHMARK.md`.
- **Option C — synthetic cross-cohort check.** Do **not** dress this up as
  external validation; it is not.

## Deferred (optional, none blocking)

- **API key.** Rate limiting now exists (in-memory, per process; see `README.md`),
  but there is still no `X-API-Key` or other authentication. Only matters if the
  Render URL is shared publicly. Suggest a single deployment key via env with 401
  tests.
- **Bulk CSV scoring.** `POST /predict/batch` (≤1000 rows) + upload UI → scored
  table + downloadable CSV. Turns the product from "calculator" to "cohort tool."
  ~half a day incl. tests. Nice-to-have, not a correctness gap.
- **README screenshot.** A UI screenshot near the top showcases the dark theme to
  reviewers/graders.
- **Render persistence.** `data/hepatiq.db` lives on ephemeral disk and resets per
  deploy. Documented; only fix if history must survive restarts (attach a disk +
  set `HEPATIQ_DB_PATH`). Blueprint comments in `render.yaml` show how.

## Known issues / cautions

- **Leaked GitHub PAT (history rewritten; containment ongoing).** `create_issues.py`
  contained a hardcoded classic GitHub PAT. The file was deleted, and all branch
  history was rewritten and force-pushed (115 commits, 12 branches, zero matches
  in 436 reachable historical file versions). The token returned HTTP 401 when
  tested, but treat it as compromised. Remaining work: verify tags, PR refs, forks,
  and caches; request a GitHub Support purge; secure or destroy the mirror backup;
  re-clone local copies; review audit logs; enable secret scanning and push
  protection; and add CI secret scanning. Do not reintroduce credentials.
- **Dependency pins are deliberate.** `requirements.txt` pins exact versions
  (e.g. `streamlit==1.62.0`). Reason: an unpinned install once pulled a newer
  Streamlit whose form-widget behaviour differed from what the tests were written
  against (an `increment()` regression caught in CI). Do not blanket-unpin.
- **CI Python is 3.12; local dev was 3.14.** Pins were verified to install on
  both. If a future pin isn't available for 3.12, relax only that package to a
  `>=` floor.
- **`data/hepatiq.db`** is gitignored and disposable; the E2E clear-history test
  wipes it. Never commit prediction logs.
- **The model is a skops artifact.** Startup verifies its SHA-256 and feature contract
  against `models/model_manifest.json`, then loads it through skops with a fixed
  trusted-type allowlist. The manifest is not a signature; never load user-uploaded
  or remotely fetched models.
- **Not a medical device.** Not FDA/CDSCO-approved, not clinically validated. Keep
  the disclaimer footer and `docs/LIMITATIONS.md` accurate.

## How to run (quick reference)

```bash
# restores to the pinned environment
pip install -r requirements.txt

# API
python -m uvicorn hepatiq.backend.main:app --host 127.0.0.1 --port 8000

# UI
python -m streamlit run src/hepatiq/frontend/app.py --server.port 8501 --server.headless true
# open http://localhost:8501  ·  API docs: http://localhost:8000/docs

# tests (CI-equivalent)
python -m pytest --cov=hepatiq.backend --cov=hepatiq.ml --cov=hepatiq.validation --cov-fail-under=60
```

Deployment: Render (backend) and Streamlit Cloud (UI) auto-redeploy from `main`.
Streamlit Cloud needs `HEPATIQ_BACKEND_URL` set in app **Secrets** to the Render
service URL; otherwise the UI calls `localhost` and fails.
