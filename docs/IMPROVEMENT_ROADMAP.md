# HepatiQ AI - Prioritized Improvement Roadmap

Forward-looking execution plan for the next engineering sessions. This document is
meant to be used, not just read: pick the first unchecked high-priority item, do
the work, run the stated verification, then update the status board and evidence.

- **Baseline date:** 2026-11-01
- **Branch:** `v2/clinical-rebuild`
- **Product status:** research prototype; not a medical device
- **Serving model:** v1 17-feature Logistic Regression pipeline at `models/model.pkl`
- **Assessment baseline:** 91 passed, 2 skipped, 74.88% local full-`src` coverage
- **CI gate:** `ruff check .` and pytest with a 60% coverage floor
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

- The backend serves the v1 Logistic Regression pipeline from `models/model.pkl`
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
- [x] Verified `ruff`, 91 passing tests, 2 skipped, and 74.88% coverage.

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
| SEC-02 | API authentication, rate limits, CORS/XSRF | P1 | Open | M | None |
| DATA-01 | Canonical v1 data lineage and provenance | P1 | Open | M | None |
| DEP-01 | Complete Docker CI, healthcheck, and image scan | P1 | Open | M | P0 Docker review |
| SEC-03 | Model artifact integrity and startup validation | P1 | Open | M | DATA-01 recommended |
| CI-01 | Dependency, action, and supply-chain guardrails | P1 | Open | S | None |
| OBS-01 | Structured logging, request IDs, readiness, metrics | P2 | Open | M | SEC-02 |
| API-01 | API versioning and contract hardening | P2 | Open | M | SEC-02 |
| PROD-01 | Bulk CSV scoring workflow | P2 | Open | M | SEC-02 |
| DEP-02 | Split runtime and development dependencies | P2 | Open | M | DEP-01 |
| PERS-01 | Persistent history storage for Render | P2 | Open | S | None |
| UI-01 | Accessibility, screenshot, and E2E depth | P2 | Open | M | None |
| QUAL-01 | Type checking and test-depth improvements | P2 | Open | M | None |
| DOC-01 | Refresh stale status docs and model card | P2 | Open | S | None |
| RES-01 | True external validation | P3 | Blocked: data access | L | Frozen model |
| RES-02 | Held-out bridge test on existing cohort | P3 | Open | S | None |
| RES-03 | Time-to-event model for censoring | P3 | Open | L | RES-01/02 |
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
authentication, no rate limit, no restricted CORS policy, and the development
compose file disables Streamlit CORS and XSRF protection.

**Scope**

- [ ] Add an `X-API-Key` dependency. Read the key from `HEPATIQ_API_KEY`.
- [ ] Keep `/health` public, but return no sensitive details.
- [ ] Fail closed when `HEPATIQ_ENV=production` and no API key is configured.
  Local development may run without a key only when the environment is not
  production.
- [ ] Add an in-memory per-client rate limiter with configurable limits for
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
- [ ] Health remains usable for platform checks.
- [ ] Rate-limit state is per process and documented as such.
- [ ] No key or client identity is written to prediction history.

**Do not:** Implement full OAuth or a user database unless a real multi-user
requirement appears. Start with a single deployment key and a documented limitation.

---

### DATA-01 - Make v1 training use the canonical 418-row cohort

**Why:** v1 trains from `data/raw/pbc.csv` (419 rows), while the v2 loader and
provenance system use `data/external/pbc.csv` (canonical 418 rows). Row 419 is
dropped by the 5-year filter, so current metrics should be unchanged, but having
two data authorities is a correctness trap.

**Steps**

- [ ] Add a regression test proving the canonical 418-row cohort and the current
  raw cohort produce identical labeled rows for the 329 retained patients,
  including `severe_event_5yr` and event count 132.
- [ ] Switch `build_5yr_target.py` to read the canonical external cohort and call
  `verify_datasets()` before reading.
- [ ] Keep `data/raw/pbc.csv` only as an archived input or remove it after the
  migration is documented.
- [ ] Regenerate `data/processed/pbc_5yr_target.csv`; confirm the model artifact and
  predictions do not change. Do not retrain unless the evidence shows a difference.
- [ ] If the model changes, record the new SHA-256, metrics, and reason in the
  execution log and `docs/model_card.md`.
- [ ] Update `data/README.md`, `docs/LIMITATIONS.md`, and path docstrings.

**Files:** `src/hepatiq/ml/build_5yr_target.py`, `src/hepatiq/paths.py`,
`src/hepatiq/data/provenance.py`, `data/README.md`, tests.

**Acceptance**

- [ ] There is one documented training source with pinned SHA-256 provenance.
- [ ] Labeled row count is 329 and event count is 132.
- [ ] A focused test fails if the canonical file is edited or replaced.
- [ ] Any model or metric change is explicit, not incidental.

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
the 17-feature contract.

**Steps**

- [ ] Create `models/model_manifest.json` containing artifact SHA-256, model type,
  feature names, training data hash, metrics, creation date, and Python/sklearn
  versions.
- [ ] Verify the artifact hash before `joblib.load`; refuse to load on mismatch.
- [ ] Validate the loaded pipeline exposes the expected feature count and, where
  available, feature names.
- [ ] Add a test where a tampered model hash causes `/health` to report unavailable
  and `/predict` to return 503 without leaking the path.
- [ ] Document that model files must never come from user upload or an untrusted
  URL.
- [ ] Evaluate `skops.io` or ONNX as a safer serialization path in a separate
  change; do not combine that migration with the hash check.

**Files:** `src/hepatiq/backend/main.py`, `models/`, new manifest, tests,
`docs/model_card.md`.

**Acceptance**

- [ ] Startup fails closed on hash mismatch.
- [ ] Feature-contract mismatch is detected before serving predictions.
- [ ] Existing valid artifact still passes the exact-reproducibility test.

---

### CI-01 - Dependency, action, and supply-chain guardrails

**Why:** CI runs tests but does not audit dependencies, pin actions by commit, or
watch for updates. Exact pins are deliberate and must stay.

**Steps**

- [ ] Add `pip-audit -r requirements.txt` with a documented severity threshold.
- [ ] Pin `actions/checkout` and `actions/setup-python` to full commit SHAs.
- [ ] Add Dependabot or Renovate for pip, GitHub Actions, and Docker base images.
- [ ] Keep updates grouped so one dependency bump is reviewable on its own.
- [ ] Add a CI timeout and pip cache; make failures actionable.
- [ ] Document the update procedure: bump, run full tests, verify model
  reproducibility, update the manifest if the artifact changes.

**Acceptance**

- [ ] CI fails on a known HIGH/CRITICAL dependency advisory.
- [ ] Actions are pinned by SHA.
- [ ] Dependency updates are proposed automatically but never merged untested.
- [ ] `requirements.txt` remains exact-pinned unless a specific exception is
  documented.

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

- [x] Mark `docs/NEXT_STEPS.md` as historical, remove the stale commit pointer and
  test count, and point readers to this roadmap.
- [ ] Update `docs/NEXT_STEPS.md` security notes and quality baseline whenever a
  later task changes them.
- Add the OOF confidence interval to `docs/model_card.md` so it matches the README
  and validation report.
- Ensure limitations remain explicit: single historical cohort, no external
  validation, no clinical benchmark superiority, no PHI controls.

## 7. P3 Research Backlog

### RES-01 - True external validation

**Blocked on data access.** The highest-value research step. Freeze
`models/model.pkl`, score a cohort it has never seen with the same features and
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
against the test fixture or the direct `joblib` inference test. A changed artifact
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
Date:
Task:
Status:
Change:
Files:
Verification:
Notes / follow-up:
```

## 12. Related Documents

- [`ROADMAP.md`](ROADMAP.md) - historical 50-day phase plan and model-selection decisions
- [`NEXT_STEPS.md`](NEXT_STEPS.md) - earlier handoff notes; partially stale after P0
- [`LIMITATIONS.md`](LIMITATIONS.md) - evidence and scope boundaries
- [`model_card.md`](model_card.md) - intended use, metrics, ethics
- [`SCORE_BENCHMARK.md`](SCORE_BENCHMARK.md) - Mayo Risk Score and UDCA benchmarks
- [`../README.md`](../README.md) - product overview and live demo
