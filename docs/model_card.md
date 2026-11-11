# HepatiQ — Model Card

- Model version: v1.0
- Repository: HepatiQ AI
- Last updated: November 2026
- Artifact SHA-256: `75fd4eb0093ca660da3a0072123bd5fb571d413c50b423b81064b2b409fbb16e`

## Model Details
- **Task**: binary classification — predict 5-year severe event risk (death or liver transplant) in patients with Primary Biliary Cholangitis (PBC)
- **Model type**: Logistic Regression (L2-regularized, `class_weight='balanced'`), selected from a three-way comparison against Random Forest and XGBoost
- **Preprocessing**: `IterativeImputer` (multivariate imputation) + `StandardScaler`, both fit fresh inside each cross-validation fold — never on the full dataset upfront — to avoid leaking held-out patients into preprocessing
- **Framework**: scikit-learn (`LogisticRegression`, `IterativeImputer`, `StandardScaler`, `Pipeline`), serialized with `skops==0.16.0`
- **Artifact verification**: startup checks `models/model.skops` SHA-256 and 17-feature contract against `models/model_manifest.json`, then loads it through skops with a hard-coded extra trusted-type allowlist (skops' library-controlled defaults also apply); verification and loading use the same byte snapshot. Mismatch leaves the model unavailable rather than serving a different artifact.
- **Trained**: September 2026
- **Team**: HepatiQ (Pranjal — backend/MLOps/lead, Nirali Verma — ML, Subbannagari Deekshitha — frontend, Rudra Singh Tomar — clinical validation), guided by Prof. Parag Gajbhiye, Anand School of Engineering and Technology, Sharda University

## Intended Use
- Clinical **decision-support** tool estimating 5-year risk of a severe event in patients already diagnosed with PBC
- **Not** a diagnostic tool, and **not** validated for general cirrhosis or other liver diseases
- Intended to supplement, not replace, clinician judgment — output is a probability score with SHAP-based explanation, not an automated decision

## Training Data
- **Source**: canonical `survival::pbc` Mayo Clinic Primary Biliary Cholangitis cohort (418 patient records), exported from CRAN `survival` 3.8-12 and pinned by SHA-256 in `data/external/PROVENANCE.json`
- **Training input**: `data/external/pbc.csv`; the builder calls `verify_datasets()` before reading. The 419-row `data/raw/pbc.csv` is retained only as archived lineage.
- **Cohort construction**: patients censored before the 5-year mark (5-year outcome unknown) were dropped — 89 of 418 — leaving **329 patients**
- **Outcome definition**: `severe_event_5yr = 1` if death or transplant occurred within 1,825 days of baseline; `0` if event-free through 5 years
- **Class balance**: 197 event-free (59.9%) vs. 132 severe event (40.1%)
- **Features (17)**: `trt` (treatment arm), `age`, `sex`, `ascites`, `hepato` (hepatomegaly), `spiders` (spider angiomata), `edema`, `bili` (serum bilirubin, mg/dL), `chol` (serum cholesterol, mg/dL), `albumin` (g/dL), `copper` (urine copper, µg/day), `alk.phos` (alkaline phosphatase, U/L), `ast`, `trig` (triglycerides, mg/dL), `platelet`, `protime` (prothrombin time, seconds), `stage` (histologic stage, 1–4)

## Evaluation
5-fold stratified cross-validation (`random_state=42`), imputation + scaling fit fresh inside each fold. Three models compared: Logistic Regression, Random Forest, XGBoost. Metrics reported as mean + 95% CI (t-distribution, df=4) across the 5 folds — not point estimates alone, since n=329 makes a single-number comparison unreliable.

| Model | ROC-AUC (95% CI) | Precision | Recall | F1 | Brier score (↓ better) |
|---|---|---|---|---|---|
| Logistic Regression | 0.880 [0.837, 0.923] | 0.767 | 0.810 | 0.786 | **0.136** |
| Random Forest | **0.884** [0.828, 0.946] | 0.723 | 0.825 | 0.769 | 0.142 |
| XGBoost | 0.870 [0.827, 0.913] | 0.722 | 0.788 | 0.750 | 0.153 |

**Out-of-fold (OOF) validation** uses the same 5-fold stratified split with a fresh pipeline per fold and 1000-resample bootstrap 95% CIs (seed 42). OOF ROC-AUC is **0.8828 [0.8409, 0.9185]** and Brier **0.1364 [0.1136, 0.1632]**, versus a class-prior baseline AUC of **0.4924 [0.4277, 0.5514]**. The OOF intervals broadly agree with the CV-fold t-intervals above (AUC 0.8373–0.9227; Brier 0.1022–0.1703).

**Calibration.** The weighted OOF model has a calibration slope of **0.725**, CITL **-0.498**, ECE **0.062**, and ICI **0.248**. Discrimination is good, but probabilities overpredict on average. Reliability diagrams are in `reports/figures/00_calibration_oof.png` and `reports/figures/01_reliability_f17_vs_f5.png`.

**Held-out clinical benchmark.** On the 70 non-randomized patients with a complete score (33 events), the fixed 1989 Mayo Risk Score reached 5-year AUC **0.851 [0.749, 0.928]** versus **0.816 [0.712, 0.905]** for v1 retrained on the 312 randomized patients. The confidence intervals overlap, so this is not proof that the Mayo score is superior — but v1 has not demonstrated added value over the five-variable score. The full-cohort Mayo AUC (0.886) is apparent because the score was derived on this cohort. Details: `docs/SCORE_BENCHMARK.md`.

### Model selection
Selected via a documented rule (`src/hepatiq/ml/train.py::select_winner`), not a bare "highest ROC-AUC" pick. Random Forest achieved the highest mean ROC-AUC (0.8844), but the ROC-AUC confidence intervals overlapped substantially across models and were therefore not statistically separable. Under HepatiQ's documented model-selection policy, calibration (Brier score) is used as the primary tie-break criterion for clinically interpretable risk estimation. Logistic Regression achieved the best calibration (Brier = 0.1363) and was therefore selected as the deployment model.

**Winner: Logistic Regression.**

The model-selection procedure is fully deterministic through fixed random seeds (`random_state=42`) and documented in `src/hepatiq/ml/train.py`.

## Explainability
Per-patient SHAP attributions via `shap.LinearExplainer` (`src/hepatiq/ml/explain.py`), appropriate here because the winning model is linear. Example: a patient with severely elevated bilirubin (14.5 mg/dL, ~14× the upper limit of normal), edema, low albumin, and stage 4 fibrosis was scored at 99.9% risk, with each of those features correctly identified as risk-increasing — consistent with known PBC prognostic markers, and matching this patient's actual observed outcome.

## Limitations
- **Disease scope**: trained exclusively on PBC patients from a single historical Mayo Clinic trial cohort. Not validated for general cirrhosis, other liver diseases, or populations outside this trial's era and demographics.
- **Sample size**: 329 patients is small for a 17-feature model. All three candidate models' 95% CIs overlap — they are not statistically distinguishable from each other on ROC-AUC alone. Treat reported performance as indicative, not precise.
- **Cohort selection bias**: 89 of the 418 canonical patients (21.3%) were dropped for being censored before the 5-year mark. If that censoring wasn't random (e.g., related to patients' health or circumstances), the remaining cohort could be biased.
- **V2 survival is research-only**: a Cox baseline using all 418 patients preserved censoring but did not clear the predeclared serving bar (OOF C-index 0.809 vs v1 0.800; delta +0.009 vs required +0.02). It improved calibration/Brier but v1 remains serving. A 254-patient 12-month landmark cohort exists, but no landmark model is implemented.
- **Calibration**: Brier score of 0.1364 [0.1136, 0.1632] and reliability diagrams are now available, but calibration is imperfect: OOF slope 0.725 and CITL -0.498 indicate overprediction on average. These are internal OOF estimates, not external validation.
- **Historical data**: the Mayo trial predates many modern PBC treatment protocols; learned risk relationships may not reflect outcomes under current standards of care.
- **No external validation**: every reported metric comes from the same historical Mayo cohort (OOF or a held-out split of it). No independent PBC cohort has confirmed generalization.
- **No PHI or deployment controls**: the project has no authentication, authorization, encryption at rest, audit logging, or PHI handling. It is a research prototype, not a deployable clinical system.
- **Artifact trust boundary**: the startup hash check detects accidental or tampered replacement, but it is not a signature. If an attacker can replace both `model.skops` and `model_manifest.json`, the check passes. skops with a fixed allowlist prevents arbitrary pickle code execution, but it is not an authenticity control and does not replace a read-only artifact mount or signed manifest. Do not load user-uploaded or remotely fetched models.
- **Not a diagnostic tool**: output is a probability estimate for decision support, not a diagnosis or treatment recommendation.
- **Integration status**: Backend and frontend are integrated with the full 17-feature workflow. The FastAPI service (`src/hepatiq/backend/main.py`) exposes `/health` and `/predict` against the trained pipeline, with per-feature SHAP contributions built once at startup. The Streamlit frontend (`src/hepatiq/frontend/app.py`) presents all 17 inputs (5 required, 12 optional with server-side imputation) and renders contributions sorted by absolute impact. Model and data paths are resolved through `src/hepatiq/paths.py`, so both services work regardless of the current working directory.

## Ethical Considerations
- Predictions should be reviewed by a qualified clinician before informing patient care; this project is for academic/research and decision-support purposes, not standalone clinical deployment.
- `sex` is used as a model feature (encoded 0=female, 1=male). Subgroup performance by sex has not been separately evaluated given the small sample size, and should be checked before any broader use.

## Future Work

- External validation using independent PBC cohorts.
- Benchmarking against GLOBE Score and UK-PBC Risk Score (both require post-UDCA or external registry data).
- Survival analysis: a research-only Cox baseline is implemented; Random Survival Forests and competing-risk extensions remain future work.
- Landmark follow-up model on the existing 254-patient cohort; not yet implemented.
- Evaluation on larger international PBC registries.

## Reproducing These Results
```
pip install -r requirements.txt && pip install -e . --no-deps

python -m hepatiq.ml.build_5yr_target   # verifies data/external/pbc.csv provenance -> processed cohort
python -m hepatiq.ml.train              # trains, cross-validates, selects, and writes the manifest
python -m hepatiq.ml.explain            # SHAP explanation for one patient
python -m hepatiq.validation.run_validation  # OOF report with bootstrap CIs
```
Full fold-by-fold numbers: `models/candidates/training_metrics.json`.

---
*HepatiQ — Anand School of Engineering and Technology, Sharda University. Guided by Prof. Parag Gajbhiye.*
