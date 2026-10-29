# Machine Learning

Model development for HepatiQ AI. Everything here imports path constants from
`hepatiq.paths`, so scripts work from any directory once the package is installed
(`pip install -e . --no-deps`).

## Files

| File | Purpose |
| --- | --- |
| `build_5yr_target.py` | Builds the labeled cohort: `data/raw/pbc.csv` → `data/processed/pbc_5yr_target.csv` |
| `impute_pipeline.py` | Standalone IterativeImputer/StandardScaler exploration pipeline → `data/interim/` |
| `train.py` | 5-fold CV comparison of LR / RF / XGBoost, selection rule, full-cohort refit |
| `explain.py` | Per-patient SHAP explanation using the deployed model |

## Running

```bash
python -m hepatiq.ml.build_5yr_target
python -m hepatiq.ml.train
python -m hepatiq.ml.explain
```

Outputs:

- `models/model.pkl` — winning pipeline refit on the full 329-patient cohort
- `models/candidates/{lr,rf,xgb}_model.pkl` — benchmark candidates
- `models/candidates/training_metrics.json` — fold-by-fold metrics

## Guidelines

- Keep imputation and scaling inside the CV pipeline (no upfront fit) to avoid
  leakage on this small cohort.
- Keep random seeds fixed (`random_state=42`); the whole pipeline is deterministic.
- Record any metric changes in `docs/model_card.md` and
  `models/candidates/training_metrics.json`.

## Related

- Data: `data/raw`, `data/processed`, `data/interim` (repo root)
- Deployed artifact: `models/model.pkl`
- Validation: `src/hepatiq/validation/`
- Serving: `src/hepatiq/backend/`
