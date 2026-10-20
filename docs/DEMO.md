# Demo Runbook

A 5-minute walkthrough of HepatiQ for reviewers or presentations. All three patient
scenarios below are verified against the live API — the numbers are what you should see.

## 1. Start (once)

```bash
# terminal 1 — API
uvicorn backend.main:app --port 8000

# terminal 2 — UI
streamlit run frontend/app.py
```

Open **http://localhost:8501**. Confirm **http://localhost:8000/health** shows
`"model_loaded": true`.

## 2. Three patients, three stories

Enter the values in the form and press **Compute risk**.

### Patient A — reassuring (expect ≈ 9.7%)

| Field | Value |
|---|---|
| Age | 45 |
| Sex | f |
| Edema | 0 |
| Bilirubin | 0.6 |
| Albumin | 4.0 |
| *(all optional blank)* | |

**Talking point:** every major contributor *lowers* risk — bilirubin −0.74,
albumin −0.51, age −0.22 (SHAP, log-odds). The chart bars point left/blue.

### Patient B — typical (expect ≈ 27.5%)

Use the form defaults unchanged (age 55, f, edema 0, bilirubin 1.0, albumin 3.5).

**Talking point:** an unremarkable panel still lands near 1 in 4 — this cohort's event
rate is 40%, so a "middle" patient is genuinely uncertain. Good moment to show that the
output is a calibrated probability, not a verdict.

### Patient C — concerning (expect ≈ 99.4%)

| Field | Value |
|---|---|
| Age | 68 |
| Sex | m |
| Edema | 0.5 |
| Bilirubin | 8.0 |
| Albumin | 2.9 |
| Ascites | 1 |
| Prothrombin time | 13.5 |
| Platelets | 180 |

**Talking point:** bilirubin +1.08 and albumin +0.75 dominate — the same markers a
clinician would eyeball, quantified. Note the male-sex contribution (+0.85): a learned
cohort association, which is exactly why `docs/LIMITATIONS.md` says SHAP explains the
model, not causation.

## 3. Show the explainability + history loop

1. After each submit, the **feature-contributions bar chart** renders (red = raises
   risk, blue = lowers; `*` marks server-side-imputed inputs).
2. Open the **"Recent predictions (local history)"** expander — all three patients
   appear newest-first with risk and top contributors, served from SQLite via
   `GET /history`.
3. Optional CLI proof of the same data: `curl http://localhost:8000/history?limit=5`.

## 4. Closing claims (safe to make)

- Leakage-controlled OOF ROC-AUC **0.8828 [0.8409, 0.9185]** vs 0.4924 class-prior
  baseline (`validation/report.md`) — reproducible: `python validation/run_validation.py`.
- API output is bit-for-bit consistent with direct model inference — enforced by 46+
  tests including a live form→API→model E2E.
- Honest limits, in writing: `docs/LIMITATIONS.md` (no INR/creatinine → no MELD;
  n=329 → wide CIs; research prototype, not a medical device).

## If something looks wrong

- Blank page / scorecard error → check `:8000/health` first; the UI shows
  "Model unavailable (503)" if the model didn't load.
- History expander empty → make at least one prediction; the file is
  `data/hepatiq.db` (gitignored, delete any time).
