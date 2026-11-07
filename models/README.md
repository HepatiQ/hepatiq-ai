# Models

Trained artifacts for HepatiQ AI.

## Layout

```text
models/
  model.pkl                        Deployed pipeline (Logistic Regression)
  model_manifest.json              Artifact hashes, feature contract, metrics
  candidates/
    lr_model.pkl                   Logistic Regression candidate
    rf_model.pkl                   Random Forest candidate
    xgb_model.pkl                  XGBoost candidate
    training_metrics.json          Fold-by-fold CV metrics + 95% CIs
```

`model.pkl` is the full-cohort refit of the winner selected by
`src/hepatiq/ml/train.py::select_winner`. The candidate files are retained for
benchmarking and audit.

> Note: `lr_model.pkl` and `model.pkl` are expected to be identical artifacts
> (the LR candidate was the winner); they are kept separately for provenance.

Paths are defined in `src/hepatiq/paths.py` (`MODEL_PATH`,
`MODEL_MANIFEST_PATH`, `CANDIDATES_DIR`, `METRICS_PATH`).

## Loading

The FastAPI backend verifies the artifact SHA-256 and the 17-feature contract
against `model_manifest.json` before calling `joblib.load()`. Verification
failure leaves the API running but unavailable (`/health` reports
`model_loaded: false`; `/predict` returns 503).

```python
import joblib

from hepatiq.backend.main import FEATURE_COLUMNS
from hepatiq.model_artifact import validate_loaded_model, verify_model_artifact
from hepatiq.paths import MODEL_MANIFEST_PATH, MODEL_PATH

verify_model_artifact(MODEL_PATH, MODEL_MANIFEST_PATH, FEATURE_COLUMNS)
model = joblib.load(MODEL_PATH)
validate_loaded_model(model, FEATURE_COLUMNS)
probability = model.predict_proba(features)[0, 1]
```

The hash check detects accidental or tampered replacement. It is not a
signature: if an attacker can replace both `model.pkl` and its manifest, the
check cannot distinguish the replacement. Never load a pickle from an
untrusted upload or URL.

## Regenerating

```bash
python -m hepatiq.ml.train
```

This rewrites `models/candidates/`, `models/model.pkl`, and
`models/model_manifest.json`. The manifest must be regenerated with any artifact
change. Record the change in `docs/model_card.md`.

## Related

- Training: `src/hepatiq/ml/`
- Serving: `src/hepatiq/backend/`
- Validation: `src/hepatiq/validation/`
