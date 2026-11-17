# Launch copy

Use the positioning in `docs/outreach/POSITIONING.md` before editing any of this. Replace bracketed placeholders with concrete links before publishing.

## GitHub release notes skeleton

**Title:** HepatiQ v1.0 — explainable PBC risk research prototype

**Body:**

This release makes the v1 serving pipeline, API, interface, and evidence package reproducible from one repository.

- FastAPI service with `/health`, `/predict`, `/predict/batch`, `/agent/reason`, `/stats`, and history endpoints.
- Streamlit interface with single-patient scoring, SHAP explanations, local history, PDF summary, and bulk CSV upload.
- Frozen `skops` model artifact verified by SHA-256 and feature contract at startup.
- Leakage-controlled validation and published-score benchmark.
- Outreach pack: technical note, evidence brief, conference abstract, demo script, and reproducibility notebook.

**Evidence:** Internal OOF ROC-AUC 0.8828 [0.8409, 0.9185]. On held-out patients, Mayo Risk Score 0.851 versus HepatiQ 0.816; intervals overlap.

**Limitations:** Research only. No external validation, no clinical approval, no PHI controls.

**CTA:** **Open the model card** at `docs/model_card.md`.

## X thread

1/ On the only held-out patients available, the 1989 Mayo Risk Score reached AUC 0.851 for 5-year PBC outcomes. Our 17-feature model reached 0.816. The intervals overlap. That result is the reason we shipped HepatiQ with its benchmark attached.

2/ HepatiQ is an explainable PBC risk research prototype. It estimates death-or-transplant risk within 5 years from 17 routine variables and shows the SHAP attributions behind each estimate.

3/ Internal out-of-fold ROC-AUC was 0.8828 [0.8409, 0.9185] on 329 patients with 132 events. That number is leakage-safe, but it is still internal. Calibration slope was 0.725, so probabilities overpredict on average.

4/ On 70 held-out patients with a complete Mayo Risk Score, the fixed five-variable score reached 0.851 and the retrained 17-feature pipeline reached 0.816. No demonstrated added value. We state that in the model card.

5/ The app, API, benchmark, and reproducibility notebook are open. **Try the demo** or **read the model card**: https://github.com/HepatiQ/hepatiq-ai

## LinkedIn post 1 — benchmark-led

The most useful result from HepatiQ is not a headline score. It is a comparison that keeps us honest.

On 70 held-out PBC patients with a complete Mayo Risk Score, the fixed 1989 score reached 5-year AUC 0.851. Our retrained 17-feature pipeline reached 0.816. The confidence intervals overlap, so neither is proven superior — but our model did not show added value on those patients.

Internally, the pipeline reached 0.8828 [0.8409, 0.9185] out-of-fold. That estimate is leakage-safe, not external. Calibration slope was 0.725, meaning probabilities overpredict on average.

We published the prototype with those numbers in the model card, the technical note, and the one-page evidence brief. The demo includes SHAP explanations and bulk CSV scoring, but the evidence package is the point.

**CTA:** Read the model card at https://github.com/HepatiQ/hepatiq-ai/blob/main/docs/model_card.md

## LinkedIn post 2 — reproducibility-led

A clinical ML demo should ship with the commands that reproduce its claims.

HepatiQ includes:

- pinned `survival::pbc` data provenance;
- a frozen `skops` model artifact with startup hash verification;
- leakage-controlled validation;
- a benchmark against the published Mayo Risk Score;
- a notebook that runs the validation and benchmark scripts.

The result is a research prototype that makes its strengths and limits inspectable. Internal OOF ROC-AUC is 0.8828 [0.8409, 0.9185]. Held-out AUC is 0.816 versus 0.851 for the Mayo Risk Score, with overlapping intervals.

**CTA:** Open the reproducibility notebook at https://github.com/HepatiQ/hepatiq-ai/blob/main/notebooks/hepatiq_reproducibility.ipynb

## Community post — ML/healthcare forums

Title: Open research prototype: explainable PBC risk model with an honest held-out benchmark

Body:

I built an open Streamlit + FastAPI prototype for 5-year severe-event risk in primary biliary cholangitis. The serving model is a regularized logistic-regression pipeline with SHAP attributions.

Internal OOF ROC-AUC is 0.8828 [0.8409, 0.9185] on 329 patients. On the only held-out patients available, the fixed Mayo Risk Score reached 0.851 and the retrained 17-feature model reached 0.816; intervals overlap. The repository includes the benchmark, model card, limitations, reproducibility notebook, and API docs.

Research only; not a medical device.

**CTA:** Read the technical note at https://github.com/HepatiQ/hepatiq-ai/blob/main/docs/outreach/TECHNICAL_NOTE.md
