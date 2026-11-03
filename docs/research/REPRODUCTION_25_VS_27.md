# Reproduction Record: 25.00% versus 27.48%

**Status:** awaiting exact `25.00%` payload; baseline `27.4847%` verified  
**Date opened:** 2026-11-02  
**Protocol:** `docs/research/FEATURE_ABLATION_IMPUTATION_AUDIT.md`

## 1. Purpose

Pin the exact inputs, units, model hash and application version behind the
reported `25.00%` prediction, and determine whether it is a different payload,
a different model, a different application version, or an unexplained
discrepancy.

The `25.00%` value is **not** treated as evidence about model quality until it
is reproduced.

## 2. Verified environment

| Item | Verified value |
|---|---|
| Repository | `C:\Users\Administrator\My-Repositories\hepatiq-ai-fresh` |
| Branch at verification | `main` |
| Local commit | `db2bf514c37f27bfbae13ab79b559350bdcee970` (`db2bf51`) |
| Commit date | 2026-11-01 15:18:45 +0000 |
| Local model | `models/model.pkl` |
| Local model SHA-256 | `BC96BB1D7399391EA103C65515A76E5F40E8A7CFD4ACDCE27D59D935020C31F1` |
| Candidate model SHA-256 | `BC96BB1D7399391EA103C65515A76E5F40E8A7CFD4ACDCE27D59D935020C31F1` |
| Model size | 267713 bytes |
| Model input features | 17 |
| Model classes | `[0, 1]` |
| `pyproject.toml` version | `2.0.0` |
| `src/hepatiq/__init__.py` version | `0.1.0` |
| Local prediction history | Empty (`predictions` table count = 0) |

Deployed `/health` response at verification time:

```json
{
  "status": "ok",
  "model_loaded": true,
  "n_features": 17,
  "model_path": "/opt/render/project/src/models/model.pkl",
  "explainer_ready": true,
  "model_version": "bc96bb1d",
  "error": null
}
```

The deployed model hash prefix `bc96bb1d` matches the local model. The deployed
application commit/version is not exposed by `/health`; it must be pinned from
the deployment record or a response header if available.

## 3. Verified baseline: Patient B

Documented default inputs in `docs/DEMO.md`:

| Field | Value | Unit |
|---|---|---|
| Age | 55 | years |
| Sex | f | categorical |
| Edema | 0 | 0/0.5/1 |
| Bilirubin | 1.0 | mg/dL |
| Albumin | 3.5 | g/dL |
| Optional fields | blank | imputed |

Direct local pipeline prediction: **0.274846560155602** (`27.4847%`).

This is consistent with the documented `≈27.5%`.

## 4. Variants tested

All variants start from the default Patient B payload and change only the
listed field.

| Variant | Prediction |
|---|---:|
| Default, 12 optional features imputed | 27.4847% |
| `protime = 10.8` | 27.5358% |
| `stage = 3` | 26.31% |
| `copper = 95` | 27.55% |
| `alk.phos = 2050` | 27.48% |
| `chol = 346` | 27.49% |
| All cohort-typical optional values | 27.61% |
| `age = 60` | 31.44% |
| `bili = 1.1` | 28.12% |
| `albumin = 3.4` | 30.59% |

These values are produced by `patient_b_sensitivity`; cohort-typical uses
medians of the 329 labeled patients. None of these tested variants produced
`25.00%`.

## 5. What is needed to reproduce `25.00%`

Please provide:

1. The exact JSON payload sent to `/predict`, including which optional fields
   were blank.
2. Units used for:
   - bilirubin;
   - albumin;
   - prothrombin time;
   - alkaline phosphatase;
   - urine copper;
   - cholesterol;
   - triglycerides;
   - platelets.
3. The app URL and application version/commit shown at the time.
4. A timestamp or screenshot, especially if the result came from the deployed
   Streamlit app.
5. The model hash displayed in the UI caption (`model <hash>`), if available.

## 6. Planned verification sequence

1. Replay the exact payload against the local `models/model.pkl` pipeline.
2. Replay the exact payload against a local FastAPI `/predict`.
3. Replay the exact payload against the deployed `/predict`.
4. Record `model_version` from each response.
5. Compare local, deployed and reported values to four decimal places.
6. If the values differ, compare model hashes and deployment commit/version
   first, then preprocessing/feature order, then API defaults.
7. If the exact payload cannot be supplied, record the value as
   **`25.00% unreproduced`** and do not use it as evidence.

## 7. Known confounders

- The default demo value is `27.48%`, not `25.00%`.
- `protime` is optional in the API but part of the Mayo five.
- `sex` is required by the API but not part of the Mayo five.
- The application exposes two different version strings (`2.0.0` in
  `pyproject.toml`, `0.1.0` in `src/hepatiq/__init__.py`).
- The deployed `/health` exposes only the model hash, not the application
  commit.
- The local SQLite history is empty, so no local run can be recovered.

## 8. Outcome

Pending. This section will be completed after the exact payload is supplied or
the value is declared unreproduced.
