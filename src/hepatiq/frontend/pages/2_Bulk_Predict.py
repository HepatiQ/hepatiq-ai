import os

import pandas as pd
import requests
import streamlit as st

MAX_ROWS = 1000
REQUIRED_COLUMNS = {"age", "sex", "edema", "bili", "albumin"}
ALLOWED_COLUMNS = {
    "trt", "age", "sex", "ascites", "hepato", "spiders", "edema",
    "bili", "chol", "albumin", "copper", "alk_phos", "ast", "trig",
    "platelet", "protime", "stage",
}


def _resolve_backend_url() -> str:
    url = os.environ.get("HEPATIQ_BACKEND_URL")
    if not url:
        try:
            url = st.secrets.get("HEPATIQ_BACKEND_URL")
        except Exception:
            url = None
    default_url = "http://localhost:8000" if os.environ.get("CI") else "https://hepatiq-ai.onrender.com"
    return (url or default_url).rstrip("/")


def _rate_limit_message(response: requests.Response) -> str:
    retry_after = (response.headers.get("Retry-After") or "").strip()
    if retry_after.isdigit():
        seconds = int(retry_after)
        unit = "second" if seconds == 1 else "seconds"
        return f"Too many requests; retry in {seconds} {unit}."
    return "Too many requests; wait a moment and try again."


BACKEND_URL = _resolve_backend_url()

st.set_page_config(page_title="HepatiQ Bulk CSV", layout="wide", page_icon="🧬")
st.title("Bulk CSV risk scoring")
st.caption(
    f"Upload up to {MAX_ROWS} rows. Required columns: "
    f"{', '.join(sorted(REQUIRED_COLUMNS))}. Batch rows are not saved to prediction history."
)

uploaded = st.file_uploader("CSV file", type=["csv"], help="Columns must match the /predict API field names.")

if uploaded is None:
    st.info("Choose a CSV file to score multiple patients at once.")
    st.stop()

try:
    df = pd.read_csv(uploaded)
except Exception as exc:
    st.error(f"Could not read CSV: {exc}")
    st.stop()

df.columns = [str(column).strip().lower().replace(" ", "_") for column in df.columns]
if "alk.phos" in df.columns:
    df = df.rename(columns={"alk.phos": "alk_phos"})

if df.empty:
    st.error("CSV has no data rows.")
    st.stop()

if len(df) > MAX_ROWS:
    st.error(f"CSV has {len(df)} rows; the limit is {MAX_ROWS}.")
    st.stop()

missing = sorted(REQUIRED_COLUMNS - set(df.columns))
if missing:
    st.error(f"Missing required column(s): {', '.join(missing)}.")
    st.stop()

unknown = sorted(set(df.columns) - ALLOWED_COLUMNS)
if unknown:
    st.error(f"Unknown column(s): {', '.join(unknown)}.")
    st.stop()

st.success(f"{len(df)} rows ready for scoring.")
st.dataframe(df.head(10), hide_index=True)

if st.button("Score batch", type="primary"):
    rows = [
        {
            key: None if pd.isna(value) else (value.item() if hasattr(value, "item") else value)
            for key, value in row.items()
        }
        for row in df.to_dict(orient="records")
    ]
    with st.spinner(f"Scoring {len(rows)} rows..."):
        try:
            response = requests.post(
                f"{BACKEND_URL}/predict/batch",
                json={"rows": rows},
                timeout=120,
            )
        except requests.exceptions.Timeout:
            st.error("Backend timed out. Try again with fewer rows.")
            st.stop()
        except requests.exceptions.RequestException as exc:
            st.error(f"Could not reach backend: {exc}")
            st.stop()

    if response.status_code == 429:
        st.error(_rate_limit_message(response))
        st.stop()
    if response.status_code != 200:
        detail = response.text[:500]
        st.error(f"Batch request failed (HTTP {response.status_code}): {detail}")
        st.stop()

    payload = response.json()
    scored = []
    for item in payload["results"]:
        prediction = item.get("prediction") or {}
        source = df.iloc[item["row"]].to_dict()
        record = {
            "row": item["row"] + 1,
            "status": "ok" if prediction else "error",
            "probability": prediction.get("probability"),
            "risk_band": prediction.get("risk_band"),
            "imputed_features": ", ".join(prediction.get("imputed_features", [])),
            "error": item.get("error"),
        }
        record.update({f"input_{key}": value for key, value in source.items()})
        scored.append(record)

    result_df = pd.DataFrame(scored)
    st.metric("Rows scored", payload["succeeded"])
    if payload["failed"]:
        st.metric("Rows rejected", payload["failed"])
    st.dataframe(result_df, hide_index=True)
    st.download_button(
        "Download results CSV",
        data=result_df.to_csv(index=False).encode("utf-8"),
        file_name="hepatiq_batch_results.csv",
        mime="text/csv",
    )
