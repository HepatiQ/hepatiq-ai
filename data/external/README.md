# External PBC datasets

These CSVs are byte-for-byte exports of the datasets shipped with the CRAN
[`survival`](https://cran.r-project.org/package=survival) package. They exist so
the Python pipeline can use the canonical, citable cohorts without an R
installation.

| File | Source object | Rows | Cols | What it is |
| --- | --- | ---: | ---: | --- |
| `pbc.csv` | `survival::pbc` | 418 | 20 | Mayo Clinic PBC trial, baseline measurements (1974–1984) |
| `pbcseq.csv` | `survival::pbcseq` | 1945 | 19 | Serial laboratory follow-up for the **same 312 randomized** patients |
| `udca.csv` | `survival::udca` | 170 | 15 | Lindor et al. 1994 UDCA trial, with event dates |
| `udca1.csv` | `survival::udca1` | 170 | 7 | One row per UDCA patient, survival-ready |
| `udca2.csv` | `survival::udca2` | 1360 | 8 | UDCA patients, one row per endpoint |

`PROVENANCE.json` records the exact package version, source tarball URL,
tarball SHA-256, per-file SHA-256, and column lists. Regenerate everything with:

```sh
pip install rdata
python scripts/export_r_datasets.py
```

## Non-negotiable caveats

- **`pbcseq` is not an independent cohort.** It is the longitudinal view of the
  same 312 Mayo patients whose baseline rows are in `pbc.csv`. Never describe a
  `pbc` → `pbcseq` comparison as external validation.
- **`pbc` is the Dickson 1989 cohort.** The 312 randomized patients are the
  derivation set for the Mayo Risk Score; the 106 non-randomized patients are
  the paper's independent validation set. A full-cohort MRS evaluation is
  therefore apparent. The 106 are the only held-out patients, but they were in
  v1's training data — retrain before calling anything external.
- **The Mayo cohort predates UDCA.** `trt` is `1 = D-penicillamine`,
  `2 = placebo`; there is no UDCA arm. Any model trained here describes
  pre-UDCA natural history, not contemporary treated disease.
- **`udca` does not contain the Mayo Risk Score inputs.** It has `bili`,
  `stage`, and a stored `riskscore`, but no `age`, `albumin`, `protime`, or
  `edema`. The stored score can be benchmarked as a published predictor, but the
  score itself cannot be recomputed from this file. Recompute it on `pbc.csv`,
  which has all five inputs, and validate the implementation with unit tests.
- **`udca1` patient 151 has zero follow-up and a missing `riskscore`.** Exclude
  that patient from survival benchmarks (leaving n = 169); the loader pins this
  anomaly so a changed file fails validation.
- **`pbcseq` carries time-varying measurements.** `day` is days since
  randomization and `futime` is days to death/transplant/censoring. Any
  landmark model must hard-mask `day <= landmark_day` and assert that no
  post-landmark row leaks into features.
- **A 12-month landmark shrinks the cohort to 254 of 312 patients.** Fifty-eight
  patients have no visit at/after day 365; 22 of them died before 365 days and
  36 were censored earlier. A landmark model conditions on survival to the
  landmark, so those patients are out of scope for Model B and remain the
  responsibility of the baseline (Model A). Among the 254 eligible patients,
  110 have an event after day 365.
- **Date columns in `udca.csv` are ISO strings.** `rdata` has no R `Date`
  constructor, so the exporter converts days-since-1970-01-01 to `YYYY-MM-DD`
  (`entry.dt`, `last.dt`, `death.dt`, `tx.dt`, `hprogress.dt`, `varices.dt`,
  `ascites.dt`, `enceph.dt`, `double.dt`, `worsen.dt`). `udca1`/`udca2` keep
  numeric `futime` in days.

## Relationship to `data/raw/pbc.csv`

`data/raw/pbc.csv` has **419** rows; canonical `survival::pbc` has **418**. The
extra row is `id = 419`, a sparse row with `trt` missing and censoring at
`time = 985` days. The other 418 rows are identical to this directory's
`pbc.csv`. Because `id = 419` is censored before 1825 days it is dropped by the
v1 5-year target filter, so v1 metrics are unaffected — but v2 should use the
canonical 418-row file with provenance rather than the augmented raw file.

## License and attribution

The `survival` package is licensed LGPL (>= 2). The datasets are redistributed
from published sources; cite the original papers when using them:

- Dickson ER, Grambsch PM, Fleming TR, Fisher LD, Langworthy A. *Prognosis in
  primary biliary cirrhosis: model for decision making.* Hepatology. 1989.
- Murtaugh PA, Dickson ER, Van Dam GM, et al. *Primary biliary cirrhosis:
  prediction of short-term survival based on repeated patient visits.*
  Hepatology. 1994.
- Lindor KD, Dickson ER, Baldus WP, et al. *Ursodeoxycholic acid in the
  treatment of primary biliary cirrhosis.* Gastroenterology. 1994.
- Fleming TR, Harrington DP. *Counting Processes and Survival Analysis.* 1991.
