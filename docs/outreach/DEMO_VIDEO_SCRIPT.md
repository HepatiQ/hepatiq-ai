# Two-minute demo video script

**Recorded demo:** [video_demo.mp4](../../video_demo.mp4)

**Format:** 1280×720, screen recording with cursor and short subtitles

**Runtime:** 02:00

**Story:** Positioning → single prediction → explanation → bulk CSV → honest benchmark → CTA

## 00:00–00:10 — Cold open

**Visual:** Hold-out benchmark table on screen. Highlight `Mayo 0.851` and `HepatiQ 0.816`.

**Narration:** "HepatiQ is an explainable PBC risk research prototype. On the only held-out patients available, a 1989 five-variable score reached AUC 0.851. Our 17-feature model reached 0.816. The intervals overlap. That result is in the model card, and it shapes everything else you'll see."

**Subtitle:** `Held-out result: 0.851 vs 0.816 — intervals overlap`

## 00:10–00:25 — What it does

**Visual:** Streamlit home screen. Pan over title, API status caption, and the 17-input form.

**Narration:** "The app estimates 5-year death-or-transplant risk for patients already diagnosed with primary biliary cholangitis. It uses 17 routine clinical and laboratory inputs. Five are required; the rest can be left blank and are imputed by the pipeline."

**Subtitle:** `17 inputs · 5 required · server-side imputation`

## 00:25–00:45 — Single prediction

**Visual:** Enter the default demo values: age 55, sex f, edema 0, bilirubin 1.0, albumin 3.5. Click **Compute risk**.

**Narration:** "A clinician or researcher enters a panel and computes risk. The backend applies the same imputation and scaling pipeline used during validation, then returns a probability, a risk band, and per-feature contributions."

**Subtitle:** `Compute risk → probability + risk band + SHAP`

## 00:45–01:00 — Explanation

**Visual:** Show the SHAP contribution chart and the risk-band badge. Point to red/teal bars and any `*` imputed markers.

**Narration:** "The chart explains the model, not the patient's biology. Red inputs pushed this estimate up; teal pushed it down. A star marks an imputed input, so you can see where the model used a modeled value instead of a measurement."

**Subtitle:** `SHAP explains the model, not causation`

## 01:00–01:20 — Bulk CSV scoring

**Visual:** Click **Bulk CSV upload** in the sidebar. Upload a small CSV with `age,sex,edema,bili,albumin`. Click **Score batch**. Show the table and the download button.

**Narration:** "For cohort exploration, the sidebar opens a bulk CSV view. It accepts up to 1,000 rows, rejects unknown columns, reports row-level errors, and exports the scored table as a CSV. Batch rows are not written to local history."

**Subtitle:** `Bulk CSV: 1,000 rows · row-level errors · CSV export`

## 01:20–01:38 — Evidence and limits

**Visual:** Show reliability plot and then the limitations card from the evidence brief.

**Narration:** "Internal out-of-fold ROC-AUC was 0.8828, but calibration is imperfect and the model overpredicts on average. There is no external validation, no MELD comparison, no PHI controls, and no clinical approval."

**Subtitle:** `Internal AUC 0.8828 · calibration slope 0.725 · no external validation`

## 01:38–02:00 — Close and CTA

**Visual:** Repository page with model card and API docs links. End card: "HepatiQ — explainable PBC risk research prototype".

**Narration:** "The useful output here is a reproducible workflow: data provenance, frozen artifact, API, interface, benchmark, and limitations in one place. Try the demo, or read the model card before interpreting any score."

**Subtitle:** `Try the demo · Read the model card`

## Recording checklist

```bash
python -m uvicorn hepatiq.backend.main:app --host 127.0.0.1 --port 8000
python -m streamlit run src/hepatiq/frontend/app.py --server.port 8501
```

- Set `HEPATIQ_BACKEND_URL=http://localhost:8000` if Streamlit does not default to local.
- Use demo CSV columns exactly: `age,sex,edema,bili,albumin`.
- Keep cursor visible and move it to the target before clicking.
- Re-inject cursor and subtitle overlays after navigation.
- Do not show real patient data.
- End on the limitation, not on an unqualified score.
