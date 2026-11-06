# Data

Mayo Clinic Primary Biliary Cholangitis (PBC) dataset and derived artifacts.

## Layout

```text
data/
  external/pbc.csv            Canonical 418-patient survival::pbc export (training source)
  external/PROVENANCE.json    Pinned package, tarball, and per-file SHA-256 checksums
  raw/pbc.csv                 Archived 419-row augmented input (lineage only, not training)
  processed/pbc_5yr_target.csv Labeled cohort after 5-year censoring filter (n=329)
  interim/pbc_imputed.csv     Exploration-only imputed frame (not used by train.py)
  interim/pbc_imputed_scaled.csv  Exploration-only imputed + scaled frame
  hepatiq.db                  Local SQLite prediction history (gitignored, disposable)
```

`src/hepatiq/paths.py` is the single source of truth for these locations
(`EXTERNAL_PBC`, `RAW_DATA`, `PROCESSED_DATA`, `INTERIM_DIR`, `DEFAULT_DB_PATH`).

## Regenerating

```bash
python -m hepatiq.ml.build_5yr_target   # data/external/pbc.csv -> processed (verifies provenance)
python -m hepatiq.ml.impute_pipeline    # processed -> interim exploration frames
```

## Notes

- **One training source.** `build_5yr_target.py` reads `data/external/pbc.csv` and
  calls `verify_datasets()` before reading, so a hand-edited or replaced CSV fails
  loudly. `data/raw/pbc.csv` is retained only for lineage.
- Do **not** use the `interim/` frames for training; `train.py` fits imputation and
  scaling inside each CV fold by design.
- No real patient identifiers are present; the source is a public research dataset.
- Never commit the local `hepatiq.db`.
