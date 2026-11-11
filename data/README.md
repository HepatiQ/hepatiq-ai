# Data

Mayo Clinic Primary Biliary Cholangitis (PBC) dataset and derived artifacts.

## Layout

```text
data/
  external/pbc.csv            Canonical 418-patient survival::pbc export (training source)
  external/PROVENANCE.json    Pinned package, tarball, and per-file SHA-256 checksums
  raw/pbc.csv                 Archived 419-row augmented input (lineage only, not training)
  processed/pbc_5yr_target.csv Labeled cohort after 5-year censoring filter (n=329)
  processed/v2_survival_cohort.csv  v2 time-to-event cohort (n=418, 186 events)
  processed/v2_landmark_cohort.csv  12-month landmark cohort (n=254, 110 events)
  processed/v2_cohort_manifest.json Source hashes, counts, and feature contracts
  interim/pbc_imputed.csv     Exploration-only imputed frame (not used by train.py)
  interim/pbc_imputed_scaled.csv  Exploration-only imputed + scaled frame
  hepatiq.db                  Local SQLite prediction history (gitignored, disposable)
```

`src/hepatiq/paths.py` is the single source of truth for these locations
(`EXTERNAL_PBC`, `RAW_DATA`, `PROCESSED_DATA`, `V2_SURVIVAL_COHORT`,
`V2_LANDMARK_COHORT`, `V2_COHORT_MANIFEST`, `INTERIM_DIR`, `DEFAULT_DB_PATH`).

## Regenerating

```bash
python -m hepatiq.ml.build_5yr_target   # data/external/pbc.csv -> processed (verifies provenance)
python -m hepatiq.data.build_cohorts    # external -> v2 survival + landmark cohorts
python -m hepatiq.ml.impute_pipeline    # processed -> interim exploration frames
```

## Notes

- **One training source.** `build_5yr_target.py` reads `data/external/pbc.csv` and
  calls `verify_datasets()` before reading, so a hand-edited or replaced CSV fails
  loudly. `data/raw/pbc.csv` is retained only for lineage.
- **v2 survival cohort.** All 418 canonical patients are retained with censoring
  intact: 186 events (death or transplant) and 232 censored. The 106
  non-randomized patients keep `trt` missing.
- **v2 landmark cohort.** Eligibility requires a visit at or after day 365; features
  come from the latest visit at or before day 365. This yields 254 patients and 110
  events. `chol_pre_landmark` is retained for auditability but excluded from the
  default feature list because it is missing for 195 of 254 patients.
- Do **not** use the `interim/` frames for training; `train.py` fits imputation and
  scaling inside each CV fold by design. The v2 cohort artifacts keep missing values
  raw for the same reason.
- No real patient identifiers are present; the source is a public research dataset.
- Never commit the local `hepatiq.db`.
