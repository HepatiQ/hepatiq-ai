# Models

Trained artifacts for HepatiQ AI.

## Layout

```text
models/
  model.pkl                        Deployed pipeline (Logistic Regression)
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

Paths are defined in `src/hepatiq/paths.py` (`MODEL_PATH`, `CANDIDATES_DIR`,
`METRICS_PATH`).

## Loading

```python
import joblib

from hepatiq.paths import MODEL_PATH

model = joblib.load(MODEL_PATH)
probability = model.predict_proba(features)[0, 1]
```

## Regenerating

```bash
python -m hepatiq.ml.train
```

This rewrites `models/candidates/` and `models/model.pkl`. Record any change in
`docs/model_card.md`.

## Related

- Training: `src/hepatiq/ml/`
- Serving: `src/hepatiq/backend/`
- Validation: `src/hepatiq/validation/`
