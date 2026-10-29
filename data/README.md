# Data

Mayo Clinic Primary Biliary Cholangitis (PBC) dataset and derived artifacts.

## Layout

```text
data/
  raw/pbc.csv                 Original 419-patient Mayo PBC records
  processed/pbc_5yr_target.csv Labeled cohort after 5-year censoring filter (n=329)
  interim/pbc_imputed.csv     Exploration-only imputed frame (not used by train.py)
  interim/pbc_imputed_scaled.csv  Exploration-only imputed + scaled frame
  hepatiq.db                  Local SQLite prediction history (gitignored, disposable)
```

`src/hepatiq/paths.py` is the single source of truth for these locations
(`RAW_DATA`, `PROCESSED_DATA`, `INTERIM_DIR`, `DEFAULT_DB_PATH`).

## Regenerating

```bash
python -m hepatiq.ml.build_5yr_target   # raw -> processed
python -m hepatiq.ml.impute_pipeline    # processed -> interim exploration frames
```

## Notes

- Do **not** use the `interim/` frames for training; `train.py` fits imputation and
  scaling inside each CV fold by design.
- No real patient identifiers are present; the source is a public research dataset.
- Never commit the local `hepatiq.db`.
