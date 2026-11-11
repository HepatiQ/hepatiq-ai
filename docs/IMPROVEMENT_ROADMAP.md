# HepatiQ AI - Prioritized Improvement Roadmap

Forward-looking execution plan for the next engineering sessions. This document is
meant to be used, not just read: pick the first unchecked high-priority item, do
the work, run the stated verification, then update the status board and evidence.

- **Baseline date:** 2026-11-11
- **Branch:** `docs/v2-research-status` (v2 research); serving remains `main`
- **Product status:** research prototype; not a medical device
- **Serving model:** v1 17-feature Logistic Regression pipeline at `models/model.skops`
- **Assessment baseline:** local full suite: 223 passed, 2 skipped; targeted
  survival suite: 6 passed; CI pending for this PR. The 2 skips are frontend
  E2E tests that need a running backend.
- **CI gate:** dependency audit, `ruff check .`, and pytest with a 60% coverage floor
- **Incident status:** exposed classic PAT returned HTTP 401; the 115-commit
  history rewrite and 12-branch force-push are reported complete
- **Open security action:** verify post-rewrite containment, enable GitHub secret
  protection, and add CI secret scanning

> The historical 50-day build plan remains in [`ROADMAP.md`](ROADMAP.md). This file
> covers remaining improvements after the P0 remediation described below.

## 1. How To Use This Document

1. Work top-down by priority. Do not start P2 work while an open P1 security or
   correctness item is actionable.
2. Create a branch named `fix/<task-id>-short-name` or `feat/<task-id>-short-name`.
3. Read the task card, linked files, and acceptance criteria before editing.
4. Change the smallest surface that satisfies the card. Add or update tests in the
   same change.
5. Run the task's verification plus the global checks in section 6.
6. Update the status board and append evidence under "Execution Log".
7. Do not commit, push, or rewrite git history unless the user explicitly asks.

**Global definition of done for every task**

- [ ] Behavior is covered by a regression test, not only a manual check.
- [ ] No secret, patient data, local database, or model path is exposed.
- [ ] `python -m ruff check .` passes.
- [ ] The CI-equivalent pytest command passes.
- [ ] Relevant docs and `docs/LIMITATIONS.md` claims remain accurate.
- [ ] The execution log records commands run and results observed.

## 2. Current Baseline

### What is already true

- The backend serves the v1 Logistic Regression pipeline from `models/model.skops`
  through FastAPI (`/health`, `/predict`, `/history`, `/agent/reason`).
- The v2 data and benchmark layer exists under `src/hepatiq/data` and
  `src/hepatiq/risk`, but it is not the serving path.
- OOF validation on the Mayo cohort reports ROC-AUC 0.8828
  [0.8409, 0.9185] against a class-prior baseline of 0.4924.
- The model has not demonstrated added value over the five-variable 1989 Mayo
  Risk Score on held-out patients.
- There is no external-cohort validation, authentication, PHI control, monitoring,
  or persistent production database.
- The application is not FDA/CDSCO approved or clinically validated.

### P0 remediation completed in the working tree

- [x] Removed shared mutable state from `ClinicalAgent`; instantiated per request.
- [x] Fixed `None` and missing SHAP impacts causing `/agent/reason` failures.
- [x] Centralized risk bands in `src/hepatiq/risk_bands.py`.
- [x] Removed model-path and exception-detail leakage from API responses.
- [x] Added server-side exception logging for model, database, and history failures.
- [x] Added `.dockerignore`, non-root Docker user, explicit `CMD`, and Python 3.12.
- [x] Aligned `pyproject.toml`, devcontainer, README, and getting-started docs on
  Python 3.12.
- [x] Added regression tests for risk boundaries, agent robustness, and error
  sanitization.
- [x] Verified `ruff`, 91 passing tests, 2 skipped, and 74.88% coverage at P0 close.

### P0 caveats still open

- [x] The P0 changes were committed before the history rewrite. This working clone
  still predates that rewrite and must be re-cloned after exporting these doc edits.
- [ ] A full Docker image build exceeded the 15-minute network timeout. Dockerfile
  validation and non-root user creation were verified, but the image was not run.
- [x] The exposed classic PAT returned HTTP 401 when tested. It was invalid at test
  time, but that does not prove it was never valid or used before the rewrite.

### Secret-history remediation completed

Reported on 2026-11-01. Treat this as an incident record, not proof that every
GitHub-side copy has been purged.

- [x] Identified the exposed classic PAT in historical `create_issues.py`.
- [x] Verified the token returned HTTP 401 from `https://api.github.com/user`.
- [x] Created an untouched mirror backup of the public repository.
- [x] Created a separate mirror and installed `git-filter-repo` 2.47.0.
- [x] Rewrote all 115 commits and replaced the token pattern with a fixed marker.
- [x] Scanned 436 reachable historical file versions; found zero pattern matches.
- [x] Force-pushed all 12 rewritten branches.
- [x] Confirmed all 12 remote branch hashes matched the rewritten local refs.
- [ ] Run an independent full-history secret scan, not only the replacement regex.
- [ ] Push and verify rewritten tags and any refs outside `refs/heads/*`.
- [ ] Inspect and clean pull-request refs, forks, releases, and Actions caches.
- [ ] Ask GitHub Support to purge cached views and unreachable public objects.
- [ ] Secure, encrypt, or destroy the mirror backup; it still contains the token.
- [ ] Re-clone the original working repository, which still has the old objects.
- [ ] Review account and organization security/audit logs for historical token use.
- [ ] Enable secret scanning, push protection, validity checks, and Dependabot.
- [ ] Add `gitleaks` or TruffleHog to CI and pre-commit.
- [ ] Remove stale commit references and token-like placeholders from current docs.
- [ ] Re-run CI and deployment checks on the rewritten `main` and active branches.

## 3. Priority Definitions

| Priority | Meaning | Rule |
| --- | --- | --- |
| **P0** | Active security or correctness risk | Fix before any feature work |
| **P1** | High-value hardening or evidence gap | Do next; small, verifiable changes |
| **P2** | Product and operability improvements | Do after P1 or when a user needs it |
| **P3** | Research and clinical evidence | Requires data, time, or external partners |

Effort: **S** = under 2 hours, **M** = half a day to two days, **L** = multi-day or
blocked on external input.

## 4. Status Board

| ID | Task | Priority | Status | Effort | Depends on |
| --- | --- | --- | --- | --- | --- |
| SEC-01 | Secret history removal and containment | P1 | Partial: rewrite done, containment open | M | GitHub Support |
| SEC-02 | API authentication, rate limits, CORS/XSRF | P1 | Partial: rate limiter done; auth/CORS open | M | None |
| DATA-01 | Canonical v1 data lineage and provenance | P1 | Done | M | None |
| DEP-01 | Complete Docker CI, healthcheck, and image scan | P1 | Open | M | P0 Docker review |
| SEC-03 | Model artifact integrity and startup validation | P1 | Done | M | DATA-01 recommended |
| CI-01 | Dependency, action, and supply-chain guardrails | P1 | Done | S | None |
| OBS-01 | Structured logging, request IDs, readiness, metrics | P2 | Open | M | SEC-02 |
| API-01 | API versioning and contract hardening | P2 | Open | M | SEC-02 |
| PROD-01 | Bulk CSV scoring workflow | P2 | Open | M | SEC-02 |
| DEP-02 | Split runtime and development dependencies | P2 | Open | M | DEP-01 |
| PERS-01 | Persistent history storage for Render | P2 | Open | S | None |
| UI-01 | Accessibility, screenshot, and E2E depth | P2 | Open | M | None |
| QUAL-01 | Type checking and test-depth improvements | P2 | Open | M | None |
| DOC-01 | Refresh stale status docs and model card | P2 | Done | S | None |
| RES-01 | True external validation | P3 | Blocked: data access | L | Frozen model |
| RES-02 | Held-out bridge test on existing cohort | P3 | Open | S | None |
| RES-03 | Time-to-event model for censoring | P3 | Partial: research baseline complete; not promoted | L | RES-01/02 |
| RES-04 | Parsimony and clinical-score comparison | P3 | Open | M | None |

## 5. P1 Task Cards

### SEC-01 - Secret history removal and post-rewrite containment

**Why:** A classic GitHub PAT was committed to a public repository. Deleting the
current file was insufficient because the credential remained in historical
objects and could have been scraped. Branch history has been rewritten, but GitHub
can retain unreachable objects, pull-request refs, caches, and forks.

**Completed**

- [x] Identified the exposed classic PAT in historical `create_issues.py`.
- [x] Tested the token; GitHub returned HTTP 401 (invalid at test time).
- [x] Created an untouched mirror backup before rewriting anything.
- [x] Rewrote a separate mirror with `git-filter-repo` 2.47.0.
- [x] Rewrote all 115 commits and replaced the token pattern with a fixed marker.
- [x] Scanned 436 reachable historical file versions; found zero matches.
- [x] Force-pushed all 12 rewritten branches.
- [x] Verified all 12 remote branch hashes matched the rewritten local refs.

**Remaining**

- [ ] Run `gitleaks` and TruffleHog against the full rewritten history; do not rely
  only on the replacement regex.
- [ ] Push and verify rewritten tags and any refs outside `refs/heads/*`.
- [ ] Inspect `refs/pull/*`, forks, releases, Actions caches, and artifacts.
- [ ] Ask GitHub Support to purge cached views and unreachable public objects.
- [ ] Secure or destroy the mirror backup; it still contains the token.
- [ ] Re-clone the original local repository; its old object database still has the
  token. Preserve uncommitted work with a patch first.
- [ ] Review account and organization security/audit logs from the exposure date
  onward for token use, workflow edits, deploy keys, webhooks, and releases.
- [ ] Enable secret scanning, push protection, validity checks, and Dependabot.
- [ ] Add a CI secret-scanning job and pre-commit hook.
- [ ] Add a short secret-handling section to `docs/TEAM_WORKFLOW.md`.
- [ ] Remove stale commit hashes and token-like placeholders from current docs.
- [ ] Re-run CI and deployment checks on the rewritten `main` and active branches.

**Files:** `.github/workflows/ci.yml`, `docs/TEAM_WORKFLOW.md`, repository refs,
GitHub settings, and local clone/backup storage.

**Acceptance**

- [ ] An independent full-history scan reports zero live credentials.
- [ ] A fresh clone contains no matching token in history.
- [ ] No matching token remains in branches, tags, PR refs, forks, or caches.
- [ ] GitHub secret scanning and push protection are enabled.
- [ ] CI fails on a deliberately planted test secret in a throwaway branch.
- [ ] The backup is encrypted with restricted access or destroyed.
- [ ] No secret value appears in logs, reports, or this document.

**Verify:** use an approved scanner against the full history, then compare local
and remote refs with `git ls-remote origin`. Do not paste scan output containing a
live secret.

---

### SEC-02 - API authentication, rate limits, and deployment hardening

**Why:** The API and UI are open to anyone who can reach the port. They have no
authentication, only a basic in-process rate limit, no restricted CORS policy,
and the development compose file disables Streamlit CORS and XSRF protection.

**Scope**

- [ ] Add an `X-API-Key` dependency. Read the key from `HEPATIQ_API_KEY`.
- [ ] Keep `/health` public, but return no sensitive details.
- [ ] Fail closed when `HEPATIQ_ENV=production` and no API key is configured.
  Local development may run without a key only when the environment is not
  production.
- [x] Add an in-memory per-client rate limiter with configurable limits for
  `/predict`, `/agent/reason`, and history endpoints. Return 429 and
  `Retry-After`. Document that a multi-instance deployment needs shared storage.
- [ ] Add restrictive CORS allowlisting from `HEPATIQ_ALLOWED_ORIGINS`.
- [ ] Add security headers at the app or platform layer.
- [ ] Remove `--server.enableCORS false --server.enableXsrfProtection false` from
  the compose frontend command. Verify the UI still works with Streamlit defaults.
- [ ] Store the API key in Render and Streamlit secrets, never in source.
- [ ] Tests: missing key returns 401, wrong key returns 401, valid key succeeds,
  repeated requests return 429, configured CORS origin succeeds, unlisted origin
  does not receive an allow header.

**Files:** `src/hepatiq/backend/main.py`, new auth/rate-limit module,
`docker-compose.yml`, `.env.example`, `render.yaml`, frontend backend client,
tests.

**Acceptance**

- [ ] Protected endpoints require a key in production mode.
- [x] Health remains usable for platform checks.
- [x] Rate-limit state is per process and documented as such.
- [x] No key or client identity is written to prediction history.

**Result (2026-11-07):** Rate limiting is implemented; API-key authentication,
CORS allowlisting, and security headers remain open. See `README.md` and
`docs/LIMITATIONS.md` for the per-process limitation.

**Do not:** Implement full OAuth or a user database unless a real multi-user
requirement appears. Start with a single deployment key and a documented limitation.

---

### DATA-01 - Make v1 training use the canonical 418-row cohort

**Why:** v1 trained from `data/raw/pbc.csv` (419 rows), while the v2 loader and
provenance system use `data/external/pbc.csv` (canonical 418 rows). Row 419 is
dropped by the 5-year filter, so metrics were expected to be unchanged, but
having two data authorities was a correctness trap.

**Steps**

- [x] Add a regression test proving the canonical 418-row cohort and the archived
  raw cohort produce identical labeled rows for the 329 retained patients,
  including `severe_event_5yr` and event count 132.
- [x] Switch `build_5yr_target.py` to read the canonical external cohort and call
  `verify_datasets()` before reading.
- [x] Keep `data/raw/pbc.csv` only as an archived input and document that status.
- [x] Regenerate `data/processed/pbc_5yr_target.csv`; confirm the model artifact and
  predictions do not change. Do not retrain unless the evidence shows a difference.
- [x] If the model changes, record the new SHA-256, metrics, and reason in the
  execution log and `docs/model_card.md`. (It did not change.)
- [x] Update `data/README.md`, `data/external/README.md`, `docs/LIMITATIONS.md`,
  `docs/model_card.md`, and path docstrings.

**Files:** `src/hepatiq/ml/build_5yr_target.py`, `src/hepatiq/paths.py`,
`src/hepatiq/data/provenance.py`, `data/README.md`, tests.

**Acceptance**

- [x] There is one documented training source with pinned SHA-256 provenance.
- [x] Labeled row count is 329 and event count is 132.
- [x] A focused test fails if the canonical file is edited or replaced.
- [x] Any model or metric change is explicit, not incidental.

**Result (2026-11-06):** Processed cohort regenerated from the canonical file:
418 loaded, 89 dropped, 329 retained, 132 events. The frozen model SHA-256 stayed
`bc96bb1d7399391ea103c65515a76e5f40e8a7cfd4acdce27d59d935020c31f1`; prediction
sum moved from `147.66190205068372` to `147.66190205043551` (max absolute delta
`4.768e-11`). The CSV diff is `age` precision only (canonical full precision vs
raw 8-decimal rounding); labels are identical.

---

### DEP-01 - Complete Docker CI, healthcheck, and image scanning

**Why:** The Dockerfile was only checked statically because the full build timed
out during dependency downloads. Non-root behavior and reproducibility need CI
coverage so this cannot regress.

**Steps**

- [ ] Run and complete `docker build -t hepatiq-ai:p0-check .`.
- [ ] Run the image as the non-root user and confirm `id -u` is 1000.
- [ ] Start the container and verify `/health` responds with the model loaded.
- [ ] Confirm `/app/data` is writable by the runtime user; confirm the SQLite
  history works in the container.
- [ ] Add a `HEALTHCHECK` that uses Python's standard library, not `curl`.
- [ ] Add a CI job that builds the image, starts it, waits for `/health`, and fails
  on container errors.
- [ ] Pin the base image by digest; document the update process.
- [ ] Add Trivy or equivalent scanning for HIGH/CRITICAL vulnerabilities and an
  SBOM artifact.
- [ ] Document the bind-mount permission caveat in `docker-compose.yml`: on Linux,
  host files may need UID/GID 1000 ownership.

**Acceptance**

- [ ] CI produces an image and a successful healthcheck.
- [ ] Container runs as UID 1000, not root.
- [ ] Image scan results are visible and triaged.
- [ ] `docker compose up` still works for local development.

**Note:** If dependency downloads remain too slow, add a BuildKit pip cache mount
and CI layer cache. Do not weaken pins to make the build faster.

---

### SEC-03 - Validate the model artifact before loading it

**Why:** `joblib.load()` deserializes a pickle, which can execute code if the
artifact is replaced or tampered with. Startup also assumes the artifact matches
the 17-feature contract. skops removes arbitrary pickle execution but still needs
a verifier and a fixed allowlist.

**Steps**

- [x] Create `models/model_manifest.json` containing artifact SHA-256, model type,
  feature names, training data hash, metrics, creation date, and Python/sklearn
  versions.
- [x] Verify the artifact hash before loading; refuse to load on mismatch.
- [x] Validate the loaded pipeline exposes the expected feature count and feature
  names.
- [x] Add a test where a tampered model hash causes `/health` to report unavailable
  and `/predict` to return 503 without leaking the path.
- [x] Document that model files must never come from user upload or an untrusted
  URL.
- [x] Evaluate `skops.io` and ONNX as safer serialization paths. Adopt skops;
  ONNX cannot convert the `IterativeImputer` on the released toolchain.
- [x] Replace the served pickle with `models/model.skops` and load it with a
  hard-coded extra trusted-type allowlist on top of skops' library defaults.
- [x] Verify and deserialize from one byte snapshot so the checked bytes are the
  loaded bytes.
- [x] Reject legacy pickle artifacts and require the loaded pipeline to expose
  feature names.

**Files:** `src/hepatiq/backend/main.py`, `src/hepatiq/model_artifact.py`,
`src/hepatiq/paths.py`, `src/hepatiq/ml/train.py`, `models/`, new manifest, tests,
`docs/model_card.md`.

**Acceptance**

- [x] Startup fails closed on hash mismatch.
- [x] Feature-contract mismatch is detected before serving predictions.
- [x] Existing valid artifact still passes the exact-reproducibility test.
- [x] skops refuses the current artifact without the project's extra allowlist; a
  type outside skops' default trusted set fails closed.
- [x] The skops artifact reproduces the frozen model's probabilities exactly.

**Result (2026-11-08):** The served artifact is now `models/model.skops`, loaded
through skops 0.16.0 with the fixed extra allowlist `numpy.dtype`,
`sklearn.impute._iterative.IterativeImputer`, and
`sklearn.impute._iterative._ImputerTriplet`. The verifier hashes and loads the same
byte snapshot, rejects legacy pickles, and requires feature names on the loaded
pipeline. Predictions and SHAP inputs remain bit-identical to the frozen model.
The leftover `models/model.pkl` was removed. The manifest remains an integrity
control, not a signature; signed manifests or read-only artifact mounts are
deployment hardening, not part of this task.

---

### CI-01 - Dependency, action, and supply-chain guardrails

**Why:** CI runs tests but does not audit dependencies, pin actions by commit, or
watch for updates. Exact pins are deliberate and must stay.

**Steps**

- [x] Add `pip-audit -r requirements.txt` with a documented severity threshold.
- [x] Pin `actions/checkout` and `actions/setup-python` to full commit SHAs.
- [x] Add Dependabot or Renovate for pip, GitHub Actions, and Docker base images.
- [x] Keep updates grouped so one dependency bump is reviewable on its own.
- [x] Add a CI timeout and pip cache; make failures actionable.
- [x] Document the update procedure: bump, run full tests, verify model
  reproducibility, update the manifest if the artifact changes.

**Acceptance**

- [x] CI fails on a known HIGH/CRITICAL dependency advisory.
- [x] Actions are pinned by SHA.
- [x] Dependency updates are proposed automatically but never merged untested.
- [x] `requirements.txt` remains exact-pinned unless a specific exception is
  documented.

**Result (2026-11-10):** `scripts/dependency_audit.py` runs `pip-audit` against
OSV and fails on HIGH/CRITICAL advisories or unknown severity; LOW/MEDIUM
advisories are reported without failing. At CI-01 merge, requirements pinned
`streamlit==1.66.1`, `pillow==13.0.0`, and `fpdf2==2.8.8`, clearing the reported
advisories; `pip-audit==2.10.1` remains pinned for reproducible CI behavior. The
workflow pins `actions/checkout` v7.0.1 and `actions/setup-python` v7.1.0 by
SHA, sets `contents: read`, caches pip, and has a 20-minute timeout. Dependabot
proposes grouped weekly minor/patch updates for pip, GitHub Actions, and Docker;
the merged updates (#46-#48) advanced the current pins to `streamlit==1.67.0`
and `fpdf2==2.9.0` while keeping `pillow==13.0.0` and `pip-audit==2.10.1`. The
update procedure is documented in `docs/TEAM_WORKFLOW.md`. A manual negative
test using the old Pillow 12.3.0 advisory returned exit 1; current requirements
return "No known vulnerabilities found." Current `main` CI passes 211 tests with
0 skipped and 82.49% coverage; the local baseline before the Dependabot batch
was 209 passed, 2 skipped, 82.04%, with the 2 skips being frontend E2E tests
that need a running backend. The model artifact was not changed.

## 6. P2 Backlog

### OBS-01 - Observability without PHI

- Add structured JSON logs with request IDs, route, status, latency, and model
  version. Never log raw patient inputs or prediction payloads.
- Add `/ready` separate from `/health`: readiness requires the model loaded and the
  database writable; liveness only requires the process.
- Record aggregate counters for predictions, failures, latency buckets, and
  rate-limit rejections.
- Add a simple local metrics endpoint or structured log contract before adopting a
  metrics backend.
- Acceptance: no input values or identifiers appear in logs; a failed dependency
  produces a clear readiness failure.

### API-01 - API contract hardening

- Version routes under `/v1` while keeping temporary aliases if needed.
- Add OpenAPI examples, response schemas for errors, and explicit status codes.
- Add request body size limits and reject unexpected fields consistently.
- Add a contract test that fails when a response field is removed or renamed.

### PROD-01 - Bulk CSV scoring

- Add `POST /predict/batch` with a row limit, schema validation, per-row errors,
  and a downloadable CSV response.
- Do not log uploaded rows. Reject files containing unexpected columns.
- Add tests for partial failures, row caps, and rate limits.
- This is a product feature, not a correctness fix; do it after SEC-02.

### DEP-02 - Split runtime and development dependencies

- Create separate runtime and dev requirement sets so the serving image does not
  install pytest, ruff, statsmodels, plotting, or training-only dependencies.
- Keep a single source of truth for versions shared by both sets.
- Verify the backend, frontend, training, and validation commands in CI.
- Measure image size and build time before and after.

### PERS-01 - Persistent history storage

- Render's disk is ephemeral. Either attach a persistent disk and set
  `HEPATIQ_DB_PATH`, or make history explicitly session-scoped and label it as such.
- Add a deployment note and a smoke test that history survives a restart when
  persistence is enabled.

### UI-01 - Accessibility and demo depth

- Add a checked-in screenshot near the README top.
- Run an accessibility pass on labels, contrast, keyboard order, and error states.
- Add one E2E test for the full form, prediction, explanation, history, and clear
  flow. Keep the existing mocked and live tests separate.

### QUAL-01 - Type and test depth

- Add a gradual `mypy` or `pyright` configuration focused on `backend`, `risk`,
  and `data`; do not block on frontend typing initially.
- Add tests for DB failure recovery, concurrent `/agent/reason` requests, and
  malformed numeric inputs.
- Add a Python 3.12/3.14 CI matrix only after confirming all pinned wheels exist
  on GitHub runners.

### DOC-01 - Documentation truth pass

- [x] Mark `docs/NEXT_STEPS.md` as historical, remove stale commit pointers and
  fixed test counts, and point readers to this roadmap.
- [x] Update the README, model card, limitations, demo, and validation README with
  canonical data lineage, OOF confidence intervals, calibration evidence, and the
  held-out Mayo benchmark.
- [x] Add the OOF confidence interval and calibration metrics to
  `docs/model_card.md` so they match the README and validation report.
- [x] Replace the stale "no reliability diagram" limitation with the measured
  calibration result and figure paths.
- [x] Update this roadmap's status board, baseline, decision log, and execution log.
- [x] Add generated `src/hepatiq/validation/calibration_plot.png` to `.gitignore`.
- [x] Ensure limitations remain explicit: single historical cohort, no external
  validation, no demonstrated clinical-score superiority, and no PHI/deployment
  controls.

## 7. P3 Research Backlog

### RES-01 - True external validation

**Blocked on data access.** The highest-value research step. Freeze
`models/model.skops` pipeline, score a cohort it has never seen with the same features and
outcome definition, and report ROC-AUC, Brier score, calibration, and 95%
bootstrap CIs against a class-prior baseline.

Candidate cohorts: UK-PBC, GLOBAL PBC/GLOBE, or a suitable Mayo/VA cohort. The
last option would also carry creatinine and INR, enabling a real MELD benchmark.

Do not tune on the external cohort. Do not call a synthetic or resampled cohort
external validation.

### RES-02 - Held-out bridge test

A deterministic 80/20 stratified hold-out on the existing 329 patients is a
weaker but honest bridge. Label it **held-out**, never **external**. Report the
frozen model or a freshly trained pipeline consistently, and include the same
confidence intervals and baseline.

### RES-03 - Time-to-event modeling

**Status:** Partial. A research-only XGBoost Cox baseline on all 418 patients was
evaluated; it improved calibration/Brier but missed the predeclared promotion bar
and is not serving.

The current target drops patients censored before five years. That can bias the
training distribution. Compare a Cox model or survival forest against the current
binary classifier on time-to-event metrics, with censoring handled explicitly.
Keep the current model as the baseline until the new model clears a predeclared
evaluation bar.

### RES-04 - Parsimony and clinical-score comparison

The 17-feature model has not shown added value over the five-variable 1989 Mayo
Risk Score on held-out patients. Evaluate whether a smaller feature set preserves
discrimination and calibration. Report decision-curve or net-benefit analysis
where the cohort supports it. Do not remove features based only on in-sample
importance.

## 8. Guardrails And Non-Goals

- **Do not claim clinical validity.** Keep the disclaimer, limitations, and
  research-prototype language. "Not a medical device" is a product constraint.
- **Do not call synthetic data external validation.** External means a genuinely
  independent cohort.
- **Do not tune on held-out or external data.** Freeze the model or document the
  retraining protocol before scoring.
- **Do not unpin dependencies without evidence.** The pins exist because an
  unpinned Streamlit release broke tests.
- **Do not expose paths, stack traces, raw inputs, or database details** in API
  responses or logs.
- **Do not commit** `data/hepatiq.db`, uploaded CSVs, secrets, or model artifacts
  from untrusted sources.
- **Do not migrate frameworks or rewrite the serving stack** without an ADR and a
  measured reason. The current FastAPI plus Streamlit stack is adequate.
- **Do not change risk thresholds** without a documented clinical/statistical
  rationale. They are communication aids, not action thresholds.
- **Do not hide uncertainty.** Wide confidence intervals and the lack of external
  validation belong in user-facing documentation.

## 9. Verification Commands

**Lint and tests**

```bash
python -m ruff check .
python -m pytest -q --cov=hepatiq.backend --cov=hepatiq.ml --cov=hepatiq.validation --cov-fail-under=60
```

On Windows, if pytest fails while cleaning its temporary directory, use an
explicit base temp path:

```powershell
python -m pytest -q --basetemp="$env:TEMP\pytest-hepatiq" --cov=src/hepatiq --cov-fail-under=60
```

**Docker**

```bash
docker build --check .
docker build -t hepatiq-ai:p0-check .
docker run --rm hepatiq-ai:p0-check id -u
docker run --rm -p 8000:8000 hepatiq-ai:p0-check
```

Then request `/health` and confirm the model is loaded. Do not add `--privileged`
or run the container as root to work around permission failures.

**Secret scan**

Use the team-approved scanner. Do not paste raw findings containing a live
credential into an issue, chat, or commit.

**Model reproducibility**

After any data or dependency change, compare predictions from the frozen model
against the test fixture or the direct model-inference parity test. A changed artifact
requires a new manifest entry and an explicit note in the execution log.

## 10. Decision Log

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-11-01 | Keep v1 Logistic Regression as the serving model | It is the locked, validated winner; v2 is a data/benchmark layer |
| 2026-11-01 | Centralize risk bands at 0.15 and 0.40 | Remove duplicated thresholds; retain descriptive, non-clinical semantics |
| 2026-11-01 | Require Python 3.12+ | `numpy==2.5.1` cannot install on 3.11; CI, Render, Docker, and devcontainer now align |
| 2026-11-01 | Run Docker as UID/GID 1000 | Reduce container privilege; validate on Linux bind mounts before production use |
| 2026-11-01 | External validation is the top research priority | One historical cohort cannot establish generalization |
| 2026-11-01 | Do not change model hyperparameters during P0 | P0 is correctness/security work; model changes require separate evaluation |
| 2026-11-01 | Rewrite all branch history and force-push | The PAT was public; deleting the file or revoking the token would not remove copies. Backup retained for forensics; 115 commits and 12 branches were rewritten and verified. |
| 2026-11-06 | Train v1 from canonical `data/external/pbc.csv`; archive the raw copy | Establish one data authority with pinned SHA-256 provenance. Labels and metrics were unchanged; the frozen model was not retrained and predictions moved by less than `5e-11`. |
| 2026-11-07 | Add an in-process rate limiter but defer API-key authentication | The public demo needs basic abuse protection without adding secret provisioning or user identity yet. Per-process state is documented; a shared store is required before multi-instance deployment. |
| 2026-11-07 | Verify the model artifact before `joblib.load()`; defer safer serialization | Detect accidental or tampered replacement and feature drift immediately, without combining the security fix with a higher-risk skops/ONNX migration. The manifest is an integrity check, not a publisher signature. |
| 2026-11-08 | Migrate serving to skops and remove the pickle artifact | Retire arbitrary pickle execution with a fixed extra trusted-type allowlist. ONNX was rejected because the released `skl2onnx` stack cannot convert `IterativeImputer`. Predictions were bit-identical after migration. |
| 2026-11-11 | Keep v1 serving after v2 Cox research baseline | The Cox model improved calibration/Brier but missed the predeclared promotion bar (C-index 0.809 vs 0.800; delta +0.009 vs +0.02). |
| 2026-11-11 | Do not use synthetic cohorts as external validation | Synthea/synthetic data is useful for QA but cannot establish clinical generalization. |

## 11. Execution Log

Append entries here when a task changes status. Keep evidence short and
reproducible.

```text
Date: 2026-11-01
Task: SEC-01
Status: Partial - history rewrite complete; containment and prevention open
Change: Identified a classic PAT in historical create_issues.py, verified HTTP
  401, created a mirror backup, rewrote a separate mirror with git-filter-repo
  2.47.0, force-pushed 12 branches, and verified remote hashes.
Files: repository history; GitHub refs/settings; local mirror backup
Verification: 115 commits rewritten; 436 reachable historical file versions
  scanned; 0 token-pattern matches; 401 from /user; 12 remote hashes matched.
Notes / follow-up: independent full-history scan, tags/PR refs/forks/caches,
  GitHub Support purge, backup destruction, local re-clone, audit-log review,
  secret scanning/push protection, and CI scanning remain open.
```

```text
Date: 2026-11-06
Task: DATA-01
Status: Done
Change: v1 builder now reads data/external/pbc.csv and calls verify_datasets()
  before reading. data/raw/pbc.csv is archived lineage only. Added tests for the
  canonical default path, provenance failure, and raw-vs-canonical label parity;
  regeneration now writes LF line endings on every platform.
Files: src/hepatiq/ml/build_5yr_target.py, src/hepatiq/paths.py,
  tests/test_build_target.py, data/processed/pbc_5yr_target.csv, data/README.md,
  data/external/README.md, docs/LIMITATIONS.md, docs/model_card.md
Verification: final focused build-target 3 passed; full suite 165 passed, 78.36%
  coverage; ruff clean. Cohort: 418 loaded, 89 dropped, 329 kept, 132 events.
  Model SHA unchanged; prediction max absolute delta 4.768e-11.
Notes / follow-up: data/processed diff is age precision only; model not retrained.
```

```text
Date: 2026-11-06
Task: DOC-01
Status: Done
Change: Synchronized docs with canonical lineage, OOF CIs, calibration metrics and
  figures, the Mayo held-out benchmark, the current test baseline, and generated
  artifact ignores.
Files: README.md, AUTHORS.md, docs/model_card.md, docs/LIMITATIONS.md,
  docs/NEXT_STEPS.md, docs/README.md, docs/DEMO.md, docs/ROADMAP.md,
  src/hepatiq/ml/README.md, src/hepatiq/validation/README.md,
  docs/IMPROVEMENT_ROADMAP.md, .gitignore
Verification: full pytest 165 passed with 78.36% coverage; ruff clean; report.md
  restored because regeneration produced a line-ending-only diff.
Notes / follow-up: GitHub issues intentionally left untouched in this change.
```

```text
Date: 2026-11-07
Task: SEC-02 (rate limiter only)
Status: Partial - rate limiting done; API-key auth, CORS, and security headers open
Change: Added a thread-safe in-process sliding-window limiter for /predict,
  /agent/reason, and GET/DELETE /history. /health and /stats stay exempt. Rejections
  return 429 with Retry-After, and the frontend shows the retry window. No API key.
Files: src/hepatiq/backend/rate_limit.py, src/hepatiq/backend/main.py,
  src/hepatiq/frontend/app.py, tests/test_rate_limit.py, tests/test_frontend.py,
  .env.example, docker-compose.yml, render.yaml, README.md, docs/LIMITATIONS.md,
  docs/NEXT_STEPS.md, docs/IMPROVEMENT_ROADMAP.md
Verification: focused 16 passed, 2 skipped; full suite 171 passed, 2 skipped,
  80.06% coverage; ruff clean. The 2 skips are live E2E tests with no local backend;
  CI starts the backend.
Notes / follow-up: Limiter state is per process. Use a shared store before scaling
  beyond one instance. Keep HEPATIQ_TRUST_PROXY_HEADERS=false when the API is
  directly exposed.
```

```text
Date: 2026-11-07
Task: SEC-03 (model artifact integrity)
Status: Partial - hash and feature-contract checks done; safer serialization open
Change: Added models/model_manifest.json and a verifier that checks the artifact
  SHA-256 and 17-feature contract before joblib.load(). Startup also validates the
  loaded pipeline feature names/count. Missing, malformed, or mismatched metadata
  fails closed: /health stays 200 with model_loaded=false and /predict returns 503.
  train.py now regenerates the manifest after writing model.pkl.
Files: src/hepatiq/model_artifact.py, src/hepatiq/backend/main.py,
  src/hepatiq/paths.py, src/hepatiq/ml/train.py, models/model_manifest.json,
  tests/test_model_artifact.py, models/README.md, README.md, docs/model_card.md,
  docs/LIMITATIONS.md, docs/NEXT_STEPS.md, docs/IMPROVEMENT_ROADMAP.md,
  .github/workflows/ci.yml
Verification: focused 19 passed; full suite 182 passed, 2 skipped, 80.94%
  CI-scoped coverage; ruff clean. Model SHA unchanged. The 2 skips are live E2E
  tests with no local backend; CI starts the backend.
Notes / follow-up: The manifest proves integrity, not authenticity. If an attacker
  can replace both model.pkl and model_manifest.json, the check passes. Evaluate
  skops.io or ONNX separately before serving artifacts from less-trusted paths.
```

```text
Date: 2026-11-08
Task: SEC-03 (safer serialization follow-up)
Status: Done - hash/feature checks plus skops allowlist
Change: Replaced models/model.pkl with models/model.skops, serialized with
  skops 0.16.0 (DEFLATE 9). Added a hard-coded extra trusted-type allowlist
  (numpy.dtype, sklearn.impute._iterative.IterativeImputer,
  sklearn.impute._iterative._ImputerTriplet) on top of skops' library defaults.
  The backend hashes and loads the same byte snapshot; legacy pickle artifacts
  and types outside skops' trusted defaults fail closed. Manifest model type and
  pipeline steps are checked against the loaded object. All model consumers now
  use the shared safe loader, and train.py writes the new artifact and manifest.
Files: src/hepatiq/model_artifact.py, src/hepatiq/backend/main.py,
  src/hepatiq/paths.py, src/hepatiq/ml/train.py, src/hepatiq/ml/explain.py,
  src/hepatiq/validation/run_validation.py, src/hepatiq/risk/benchmark.py,
  src/hepatiq/research/imputation.py, models/model.skops,
  models/model_manifest.json, requirements.txt, tests, docs, README.md
Verification: full suite 201 passed, 2 skipped, 82.04% CI-scoped coverage; ruff
  clean. Required-input probability 0.2801766578461799 and full-input probability
  0.10090583019835869 are bit-identical to the frozen pickle. skops without the
  project's extra allowlist raises UntrustedTypesFoundException.
Notes / follow-up: The manifest is still unsigned. An attacker who can replace
  both artifact and manifest bypasses integrity checks; use a signed manifest or
  read-only artifact mount for a stronger authenticity boundary.
```

```text
Date: 2026-11-09
Task: CI-01
Status: Done
Change: Added scripts/dependency_audit.py, which runs pip-audit against OSV and
  fails on HIGH/CRITICAL or unknown severity while reporting LOW/MEDIUM. Pinned
  pip-audit 2.10.1. Bumped streamlit to 1.66.1 (needed for pillow<14), pillow to
  13.0.0, and fpdf2 to 2.8.8 to clear the reported advisories. Pinned checkout
  and setup-python Actions by SHA, added contents: read, a 20-minute timeout, and
  explicit pip cache dependency path. Added weekly Dependabot groups for pip,
  GitHub Actions, and Docker. Documented the update/reproducibility procedure.
Files: scripts/dependency_audit.py, tests/test_dependency_audit.py,
  requirements.txt, .github/workflows/ci.yml, .github/dependabot.yml,
  docs/TEAM_WORKFLOW.md, docs/IMPROVEMENT_ROADMAP.md
Verification: current requirements audit -> "No known vulnerabilities found";
  negative gate test with pillow 12.3.0 / CVE-2026-96778 -> HIGH, exit 1.
  Clean Python 3.12.13 env from the new pins: 209 passed, 2 skipped, 82.49%
  CI-scoped coverage. Local Python 3.14: 209 passed, 2 skipped, 82.04%; ruff
  clean.
Notes / follow-up: Dependabot is a repository setting; confirm it is enabled in
  GitHub after this config lands. The manifest remains unsigned. CI secret
  scanning and push protection remain separate SEC-01 follow-ups.
```

```text
Date: 2026-11-10
Task: CI-01 documentation follow-up
Status: Done
Change: Reconciled the roadmap with the merged Dependabot updates (#46-#48).
  No code or dependency changes in this docs-only pass.
Files: docs/IMPROVEMENT_ROADMAP.md
Verification: main CI run 42803894517: 211 passed, 0 skipped, 82.49% coverage.
  Current pins: streamlit 1.67.0, pillow 13.0.0, fpdf2 2.9.0, pip-audit 2.10.1;
  Actions checkout v7.0.1 and setup-python v7.1.0.
Notes / follow-up: The local 209-passed baseline is retained for environments
  without a running backend; the two local skips are frontend E2E tests.
```

```text
Date: 2026-11-11
Task: RES-03 (v2 data slice)
Status: Done
Change: Added the censoring-aware survival cohort (418 patients / 186 events /
  232 censored) and the 12-month landmark cohort (254 / 110 / 144), with pinned
  provenance, a manifest, a CLI, tests, and data documentation. Generated v2 CSVs
  were committed.
Files: src/hepatiq/data/cohorts.py, src/hepatiq/data/build_cohorts.py,
  tests/test_v2_cohorts.py, data/processed/v2_survival_cohort.csv,
  data/processed/v2_landmark_cohort.csv, data/processed/v2_cohort_manifest.json,
  data/README.md
Verification: cohort tests passed; full suite 217 passed, 2 skipped at data-slice
  close; ruff clean.
Notes / follow-up: the landmark model is not implemented; chol_pre_landmark is
  excluded from the default feature contract.
```

```text
Date: 2026-11-11
Task: RES-03 (v2 survival baseline)
Status: Partial - research baseline complete; not promoted
Change: Added an XGBoost Cox baseline on all 418 patients, leakage-controlled
  out-of-fold evaluation against v1, Breslow absolute risk, candidate artifacts,
  and contract/serialization tests.
Files: src/hepatiq/survival/model.py, src/hepatiq/survival/evaluation.py,
  src/hepatiq/survival/train_survival.py, src/hepatiq/survival/__init__.py,
  tests/test_survival_model.py, src/hepatiq/paths.py,
  models/candidates/survival_cox.json, models/candidates/survival_metrics.json
Verification: OOF C-index 0.809 [0.777, 0.840] vs v1 0.800 [0.769, 0.829];
  delta +0.009; 5-year AUC 0.882 vs 0.873; Brier 0.1376 vs 0.1419; calibration
  slope 0.884 vs 0.635. Targeted 6 passed; full suite 223 passed, 2 skipped;
  ruff clean.
Notes / follow-up: the +0.02 promotion bar was not met; the serving model is
  unchanged. The landmark model remains unimplemented.
```

```text
Date: 2026-11-11
Task: DOC-01 (v2 status correction)
Status: Done
Change: Corrected README, AUTHORS, and status docs to state that v1 remains the
  serving model, the v2 Cox baseline is research-only and missed its promotion
  bar, the landmark model is not implemented, and synthetic data is not external
  validation.
Files: README.md, AUTHORS.md, docs/model_card.md, docs/LIMITATIONS.md,
  docs/NEXT_STEPS.md, docs/DEMO.md, docs/IMPROVEMENT_ROADMAP.md,
  docs/research/FEATURE_ABLATION_IMPUTATION_AUDIT.md
Verification: docs-only change; pytest 223 passed, 2 skipped; ruff clean.
Notes / follow-up: no code, model, data, dependency, or serving changes.
```

## 12. Related Documents

- [`ROADMAP.md`](ROADMAP.md) - historical 50-day phase plan and model-selection decisions
- [`NEXT_STEPS.md`](NEXT_STEPS.md) - historical Phase 5 handoff notes; see this roadmap for current status
- [`LIMITATIONS.md`](LIMITATIONS.md) - evidence and scope boundaries
- [`model_card.md`](model_card.md) - intended use, metrics, ethics
- [`SCORE_BENCHMARK.md`](SCORE_BENCHMARK.md) - Mayo Risk Score and UDCA benchmarks
- [`../README.md`](../README.md) - product overview and live demo
