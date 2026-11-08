# Models

Trained artifacts for HepatiQ AI.

## Layout

```text
models/
  model.skops                      Deployed pipeline (Logistic Regression)
  model_manifest.json              Artifact hashes, feature contract, metrics
  candidates/
    lr_model.pkl                   Logistic Regression candidate
    rf_model.pkl                   Random Forest candidate
    xgb_model.pkl                  XGBoost candidate
    training_metrics.json          Fold-by-fold CV metrics + 95% CIs
```

`model.skops` is the full-cohort refit of the winner selected by
`src/hepatiq/ml/train.py::select_winner`. The candidate files are retained for
benchmarking and audit; they stay in joblib format because they are not loaded by
the serving process.

> Note: the LR candidate and the deployed pipeline contain the same fitted model
> (the LR candidate was the winner), but `model.skops` uses safer skops
> serialization rather than pickle.

Paths are defined in `src/hepatiq/paths.py` (`MODEL_PATH`,
`MODEL_MANIFEST_PATH`, `CANDIDATES_DIR`, `METRICS_PATH`).

## Loading

The FastAPI backend verifies the artifact SHA-256 and the 17-feature contract
against `model_manifest.json`, then loads it through skops with a fixed extra
trusted-type allowlist on top of skops' library-controlled defaults. Verification and deserialization use the same byte
snapshot. Failure leaves the API running but unavailable (`/health` reports
`model_loaded: false`; `/predict` returns 503).

```python
from hepatiq.backend.main import FEATURE_COLUMNS
from hepatiq.model_artifact import load_verified_model
from hepatiq.paths import MODEL_MANIFEST_PATH, MODEL_PATH

model, artifact_hash = load_verified_model(
    MODEL_PATH, MODEL_MANIFEST_PATH, FEATURE_COLUMNS
)
probability = model.predict_proba(features)[0, 1]
```

The hash check detects accidental or tampered replacement. It is not a
signature: if an attacker can replace both `model.skops` and its manifest, the
check cannot distinguish the replacement. skops blocks arbitrary pickle code
execution, but a signed manifest or read-only artifact mount is still required
for a stronger authenticity boundary. Never load a model from an untrusted
upload or URL.

## Regenerating

```bash
python -m hepatiq.ml.train
```

This rewrites `models/candidates/`, `models/model.skops`, and
`models/model_manifest.json`. The manifest must be regenerated with any artifact
change. Record the change in `docs/model_card.md`.

## Related

- Training: `src/hepatiq/ml/`
- Serving: `src/hepatiq/backend/`
- Validation: `src/hepatiq/validation/`
