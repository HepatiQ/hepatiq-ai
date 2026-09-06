# HepatiQ — Model Card

## Model Details
- **Task**: binary classification — predict 5-year severe event risk (death or liver transplant) in patients with Primary Biliary Cholangitis (PBC)
- **Model type**: Logistic Regression (L2-regularized, `class_weight='balanced'`), selected from a three-way comparison against Random Forest and XGBoost
- **Preprocessing**: `IterativeImputer` (multivariate imputation) + `StandardScaler`, both fit fresh inside each cross-validation fold — never on the full dataset upfront — to avoid leaking held-out patients into preprocessing
- **Framework**: scikit-learn (`LogisticRegression`, `IterativeImputer`, `StandardScaler`, `Pipeline`), serialized with `joblib`
- **Trained**: September 2026
- **Team**: HepatiQ (Pranjal "Meet" — backend/MLOps/lead, Nirali Verma — ML, Subbannagari Deekshitha — frontend, Rudra Singh Tomar — clinical validation), guided by Prof. Parag Gajbhiye, Anand School of Engineering and Technology, Sharda University

## Intended Use
- Clinical **decision-support** tool estimating 5-year risk of a severe event in patients already diagnosed with PBC
- **Not** a diagnostic tool, and **not** validated for general cirrhosis or other liver diseases
- Intended to supplement, not replace, clinician judgment — output is a probability score with SHAP-based explanation, not an automated decision

## Training Data
- **Source**: Mayo Clinic Primary Biliary Cholangitis trial dataset (Kaggle variant, 419 patient records)
- **Cohort construction**: patients censored before the 5-year mark (5-year outcome unknown) were dropped — 90 of 419 — leaving **329 patients**
- **Outcome definition**: `severe_event_5yr = 1` if death or transplant occurred within 1,825 days of baseline; `0` if event-free through 5 years
- **Class balance**: 197 event-free (59.9%) vs. 132 severe event (40.1%)
- **Features (17)**: `trt` (treatment arm), `age`, `sex`, `ascites`, `hepato` (hepatomegaly), `spiders` (spider angiomata), `edema`, `bili` (serum bilirubin, mg/dL), `chol` (serum cholesterol, mg/dL), `albumin` (g/dL), `copper` (urine copper, µg/day), `alk.phos` (alkaline phosphatase, U/L), `ast`, `trig` (triglycerides, mg/dL), `platelet`, `protime` (prothrombin time, seconds), `stage` (histologic stage, 1–4)

## Evaluation
5-fold stratified cross-validation (`random_state=42`), imputation + scaling fit fresh inside each fold. Three models compared: Logistic Regression, Random Forest, XGBoost. Metrics reported as mean + 95% CI (t-distribution, df=4) across the 5 folds — not point estimates alone, since n=329 makes a single-number comparison unreliable.

| Model | ROC-AUC (95% CI) | Precision | Recall | F1 | Brier score (↓ better) |
|---|---|---|---|---|---|
| Logistic Regression | 0.880 [0.837, 0.923] | 0.767 | 0.810 | 0.786 | **0.136** |
| Random Forest | **0.887** [0.828, 0.946] | 0.728 | 0.810 | 0.765 | 0.141 |
| XGBoost | 0.870 [0.827, 0.913] | 0.711 | 0.780 | 0.740 | 0.155 |

### Model selection
Selected via a documented rule (`ml/train.py::select_winner`), not a bare "highest ROC-AUC" pick. Random Forest has the highest point-estimate ROC-AUC, but its 95% CI overlaps Logistic Regression's almost entirely — not a statistically distinguishable difference at this sample size. Falling through to clinical/statistical tie-breakers: Logistic Regression and Random Forest tie exactly on recall (0.8105); Logistic Regression then wins on calibration (Brier 0.136 vs. 0.141) and also has higher precision.

**Winner: Logistic Regression.**

This result has been independently reproduced twice — once in this environment and once in a separate local run — with byte-identical Logistic Regression fold scores in both, and the same model selected as winner in both despite Random Forest's higher raw ROC-AUC in each run.

## Explainability
Per-patient SHAP attributions via `shap.LinearExplainer` (`ml/explain.py`), appropriate here because the winning model is linear. Example: a patient with severely elevated bilirubin (14.5 mg/dL, ~14× the upper limit of normal), edema, low albumin, and stage 4 fibrosis was scored at 99.9% risk, with each of those features correctly identified as risk-increasing — consistent with known PBC prognostic markers, and matching this patient's actual observed outcome.

## Limitations
- **Disease scope**: trained exclusively on PBC patients from a single historical Mayo Clinic trial cohort. Not validated for general cirrhosis, other liver diseases, or populations outside this trial's era and demographics.
- **Sample size**: 329 patients is small for a 17-feature model. All three candidate models' 95% CIs overlap — they are not statistically distinguishable from each other on ROC-AUC alone. Treat reported performance as indicative, not precise.
- **Cohort selection bias**: ~21% of the original 419 patients (90) were dropped for being censored before the 5-year mark. If that censoring wasn't random (e.g., related to patients' health or circumstances), the remaining cohort could be biased.
- **Calibration**: Brier score of 0.136 indicates reasonable but imperfect calibration; a full reliability diagram has not yet been produced.
- **Historical data**: the Mayo trial predates many modern PBC treatment protocols; learned risk relationships may not reflect outcomes under current standards of care.
- **Not a diagnostic tool**: output is a probability estimate for decision support, not a diagnosis or treatment recommendation.
- **Integration status**: `backend/main.py` and `frontend/app.py` are not yet updated to this model's full 17-feature interface — they still reflect an earlier 5-biomarker placeholder scope. The model itself is trained and validated; the deployed app is not yet wired to it.

## Ethical Considerations
- Predictions should be reviewed by a qualified clinician before informing patient care; this project is for academic/research and decision-support purposes, not standalone clinical deployment.
- `sex` is used as a model feature (encoded 0=female, 1=male). Subgroup performance by sex has not been separately evaluated given the small sample size, and should be checked before any broader use.

## Reproducing These Results
```
python ml/build_5yr_target.py   # data/pbc.csv -> data/pbc_5yr_target.csv
python ml/train.py              # trains, cross-validates, and selects the winner
python ml/explain.py            # SHAP explanation for one patient
```
Full fold-by-fold numbers: `models/training_metrics.json`.

---
*HepatiQ — Anand School of Engineering and Technology, Sharda University. Guided by Prof. Parag Gajbhiye.*
