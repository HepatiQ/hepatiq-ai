# HepatiQ: one-page evidence brief

**What it is:** A research prototype that estimates 5-year death-or-transplant risk in Primary Biliary Cholangitis (PBC) from 17 routine clinical and laboratory variables and shows which inputs drove the estimate.

**What it is not:** A diagnostic tool, a validated clinical decision aid, a medical device, or a replacement for specialist judgment.

## The evidence in four numbers

| Result | Value | How to read it |
| --- | ---: | --- |
| Internal OOF ROC-AUC | 0.8828 [0.8409, 0.9185] | Leakage-safe discrimination on 329 Mayo-cohort patients |
| Held-out Mayo Risk Score AUC | 0.851 [0.749, 0.928] | Fixed 1989 five-variable score |
| Held-out HepatiQ AUC | 0.816 [0.712, 0.905] | Retrained 17-feature pipeline |
| Calibration slope | 0.725 | Probabilities overpredict on average |

The held-out comparison used 70 non-randomized patients with a complete Mayo Risk Score and 33 events. The confidence intervals overlap. The honest conclusion is that HepatiQ has **not demonstrated added value** over the Mayo Risk Score on the only held-out patients available.

## What the explanation shows

The interface displays SHAP attributions for each prediction. These describe how the fitted model used inputs such as bilirubin, albumin, age, and edema. They do **not** show causal effects and should not be read as treatment targets. Missing optional inputs are imputed before prediction; the interface marks them with `*` and the PDF summary lists them explicitly.

## What this prototype can support

- Exploring how a simple, interpretable model estimates 5-year severe-event risk on historical PBC data.
- Comparing that model's internal estimate with a published clinical score.
- Showing which measured or imputed features moved an individual estimate up or down.
- Reproducing the benchmark from pinned data and frozen model artifacts.

## What this prototype cannot support

- No external validation on a modern or independent PBC cohort.
- No claim of superiority over the Mayo Risk Score.
- No MELD comparison: the dataset lacks INR and creatinine.
- No use with real patient data: no authentication, PHI controls, audit logging, or monitoring.
- No clinical deployment claim: research use only.

## Bottom line

HepatiQ is useful as an open, explainable example of clinical ML evaluation. It is most valuable when the held-out benchmark and limitations are presented alongside the demo.

**CTA:** **Try the demo** at `https://hepatiq-ai.streamlit.app` or **read the model card** at `docs/model_card.md`.
