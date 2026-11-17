# HepatiQ outreach positioning

## Core positioning

HepatiQ is an explainable PBC risk research prototype. It estimates 5-year death-or-transplant risk from 17 routine clinical and laboratory features using a logistic-regression pipeline with SHAP explanations, and exposes the workflow through a Streamlit UI and FastAPI service. It is not a medical device and has no external validation.

## Campaign angle

The honest benchmark is the story. On the only held-out patients available, the fixed five-variable 1989 Mayo Risk Score reached AUC 0.851 versus 0.816 for the retrained 17-feature HepatiQ pipeline; the confidence intervals overlap. The prototype is worth sharing because it makes that result visible, reproducible, and explainable — not because it claims clinical superiority.

## Audience one-liners

- **Researchers:** A reproducible, leakage-controlled PBC risk pipeline with SHAP explanations and an explicit held-out benchmark against the Mayo Risk Score.
- **Developers:** A small, runnable FastAPI + Streamlit application with bulk CSV scoring, model-artifact verification, and a documented API.
- **Clinicians:** A research-only risk visualization that shows which measured inputs drove an estimate and states exactly where the evidence stops.

## Claims we can make

- Internal out-of-fold ROC-AUC is 0.8828 [0.8409, 0.9185] on 329 patients with 132 events.
- The API output matches direct model inference; this is asserted in the test suite.
- The deployed model is Logistic Regression selected by a documented rule using Brier score as the tie-break.
- SHAP attributions explain the fitted model, not causation.
- On 70 held-out patients with a complete Mayo Risk Score, Mayo AUC was 0.851 [0.749, 0.928] versus 0.816 [0.712, 0.905] for HepatiQ; intervals overlap.
- Calibration is imperfect: OOF slope 0.725, CITL -0.498, ECE 0.062.

## Claims we cannot make

- We cannot claim better performance than the Mayo Risk Score on held-out patients.
- We cannot claim external validation.
- We cannot claim clinical validity, regulatory approval, or readiness for real patient data.
- We cannot interpret SHAP values as treatment effects.
- We cannot claim MELD comparison; INR and creatinine are absent from the dataset.

## Calls to action

- Researchers: **Read the technical note** and run the reproducibility notebook.
- Developers: **Try the live demo** and open the API docs.
- Clinicians: **Read the one-page evidence brief** before interpreting any output.

## Voice rules

- Lead with the number, artifact, or limitation.
- Use "research prototype" in every public introduction.
- Say "associated with higher model risk", not "causes risk".
- Never use "game-changing", "revolutionary", "cutting-edge", or "clinically validated".
- End with one specific CTA, never "learn more".
