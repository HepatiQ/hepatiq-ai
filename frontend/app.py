import json
import os
import time
from datetime import datetime
from pathlib import Path

import plotly.graph_objects as go
import requests
import streamlit as st
from fpdf import FPDF


def _resolve_backend_url() -> str:
    url = os.environ.get("HEPATIQ_BACKEND_URL")
    if not url:
        try:
            url = st.secrets.get("HEPATIQ_BACKEND_URL")
        except Exception:
            url = None
    # Default to deployed backend; allow overrides for local dev
    return (url or "https://hepatiq-ai.onrender.com").rstrip("/")


BACKEND_URL = _resolve_backend_url()

LOGO_PATH = Path(__file__).resolve().parent / "assets" / "logo.png"

# An identical payload resubmitted inside this window is treated as a rapid
# double-click: the stored result is reused instead of POSTing (and logging) again.
SUBMIT_DEDUPE_WINDOW_S = 5.0

st.set_page_config(
    page_title="HepatiQ",
    layout="wide",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "🧬",
)

# Backend status indicator
with st.sidebar:
    st.markdown("### System Status")
    try:
        _health = requests.get(f"{BACKEND_URL}/health", timeout=3)
        if _health.status_code == 200:
            st.success("Backend: Online")
        else:
            st.warning(f"Backend: Issue (HTTP {_health.status_code})")
    except requests.exceptions.Timeout:
        st.warning("Backend: Waking up (cold start)")
    except requests.exceptions.RequestException:
        st.error("Backend: Unreachable")
    st.caption("API: " + BACKEND_URL)
    try:
        _stats = requests.get(f"{BACKEND_URL}/stats", timeout=3)
        if _stats.status_code == 200:
            s = _stats.json()
            st.markdown("### Predictions")
            st.metric("Total", s.get("total", 0))
            st.metric("High Risk", f"{s.get('high_risk_count', 0)} ({s.get('high_risk_pct', 0)}%)")
    except Exception:
        pass
    st.divider()

st.markdown(
    """
    <style>
    .stApp { background: linear-gradient(180deg, #0e1117 0%, #141924 100%); }
    section[data-testid="stSidebar"] { background: #131722; }
    h1, h2, h3 { color: #e8ecf1 !important; letter-spacing: -0.01em; }
    h1 { font-weight: 700 !important; }
    .stMetric {
        background: linear-gradient(135deg, #1a2332 0%, #1e2a3a 100%);
        border: 1px solid #2a3a4e;
        border-radius: 12px;
        padding: 18px 22px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.3);
    }
    .stMetric label { color: #8899aa !important; font-size: 0.95rem !important; }
    .stMetric [data-testid="stMetricValue"] {
        font-size: 2.8rem !important; font-weight: 700 !important;
        color: #00d4aa !important;
    }
    div[data-testid="stExpander"] {
        background: #161c28; border: 1px solid #253040; border-radius: 10px;
    }
    div[data-testid="stExpander"] summary { color: #c0c8d4 !important; }
    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #00b496, #00d4aa);
        color: #0e1117; font-weight: 700; border: none;
        border-radius: 8px; padding: 0.5em 1.6em; transition: all 0.2s;
    }
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 0 14px rgba(0,212,170,0.45); transform: translateY(-1px);
    }
    footer, .stDecoration { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

if LOGO_PATH.exists():
    _logo_col = st.columns([4, 1, 4])[1]
    _logo_col.image(str(LOGO_PATH), width="stretch")

st.markdown(
    "<h1 style='text-align:center; padding-top:0.1em; margin-bottom:0.1em; "
    "font-size:3.4rem; font-weight:800;'>HepatiQ</h1>"
    "<p style='text-align:center; color:#7a8a9a; font-size:1.05em; margin-top:0;'>"
    "5-Year Severe Event Risk Calculator · Primary Biliary Cholangitis</p>",
    unsafe_allow_html=True,
)

DISPLAY_NAMES = {
    "trt": "Treatment", "age": "Age", "sex": "Sex", "ascites": "Ascites",
    "hepato": "Hepatomegaly", "spiders": "Spiders", "edema": "Edema",
    "bili": "Bilirubin", "chol": "Cholesterol", "albumin": "Albumin",
    "copper": "Copper", "alk.phos": "Alk. Phos", "ast": "AST",
    "trig": "Triglycerides", "platelet": "Platelet", "protime": "Protime",
    "stage": "Stage",
}


def _risk_band(probability: float) -> str:
    if probability >= 0.40:
        return "high"
    elif probability >= 0.15:
        return "intermediate"
    else:
        return "low"


def optional_number(label, min_value, max_value, format, step):
    return st.number_input(
        label, min_value=min_value, max_value=max_value, value=None, format=format, step=step
    )


def fetch_history(limit: int = 10, risk_band: str = None) -> dict:
    """GET /history; never raises — returns {items, error, limit} for state."""
    try:
        params = {"limit": limit}
        if risk_band and risk_band != "All":
            params["risk_band"] = risk_band
        hr = requests.get(f"{BACKEND_URL}/history", params=params, timeout=30)
        if hr.status_code == 200:
            return {
                "items": hr.json().get("items", []),
                "error": None,
                "limit": limit,
            }
        return {
            "items": None,
            "error": f"History unavailable (HTTP {hr.status_code}).",
            "limit": limit,
        }
    except requests.exceptions.Timeout:
        return {
            "items": None,
            "error": (
                "Backend is waking up (cold start) — please refresh in a few seconds."
            ),
            "limit": limit,
        }
    except requests.exceptions.RequestException:
        return {
            "items": None,
            "error": "Backend not reachable — history hidden.",
            "limit": limit,
        }


with st.form("patient_calculator_form"):
    st.subheader("Required")
    c1, c2, c3 = st.columns(3)
    with c1:
        age = st.number_input("Age (years)", min_value=0.0, max_value=120.0, value=55.0, format="%.1f", step=1.0)
    with c2:
        sex = st.selectbox("Sex", options=["f", "m"], index=0)
    with c3:
        edema = st.selectbox("Edema (0, 0.5, 1)", options=[0.0, 0.5, 1.0], index=0)
    c1, c2 = st.columns(2)
    with c1:
        bili = st.number_input("Bilirubin (mg/dL)", min_value=0.0, max_value=100.0, value=1.0, format="%.2f", step=0.1)
    with c2:
        albumin = st.number_input("Albumin (g/dL)", min_value=0.0, max_value=10.0, value=3.5, format="%.2f", step=0.1)

    st.subheader("Optional (blank = imputed)")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        trt = st.selectbox("Treatment arm", options=[None, 1.0, 2.0], index=0)
    with c2:
        ascites = st.selectbox("Ascites (0/1)", options=[None, 0.0, 1.0], index=0)
    with c3:
        hepato = st.selectbox("Hepatomegaly (0/1)", options=[None, 0.0, 1.0], index=0)
    with c4:
        spiders = st.selectbox("Spiders (0/1)", options=[None, 0.0, 1.0], index=0)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        chol = optional_number("Cholesterol (mg/dL)", 0.0, 5000.0, "%.1f", 1.0)
    with c2:
        copper = optional_number("Urine copper (ug/day)", 0.0, 1000.0, "%.1f", 1.0)
    with c3:
        alk_phos = optional_number("Alk. Phos (U/L)", 0.0, 50000.0, "%.1f", 1.0)
    with c4:
        ast = optional_number("AST (U/L)", 0.0, 10000.0, "%.2f", 0.1)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        trig = optional_number("Triglycerides (mg/dL)", 0.0, 10000.0, "%.1f", 1.0)
    with c2:
        platelet = optional_number("Platelets (thousands/uL)", 1.0, 1000.0, "%.0f", 1.0)
    with c3:
        protime = optional_number("Prothrombin time (sec)", 1.0, 100.0, "%.1f", 0.1)
    with c4:
        stage = st.selectbox("Histologic stage (1-4)", options=[None, 1.0, 2.0, 3.0, 4.0], index=0)

    submitted = st.form_submit_button("Compute risk")

if submitted:
    payload = {
        "age": float(age),
        "sex": sex,
        "edema": float(edema),
        "bili": float(bili),
        "albumin": float(albumin),
    }
    for key, val in {
        "trt": trt, "ascites": ascites, "hepato": hepato, "spiders": spiders,
        "chol": chol, "copper": copper, "alk_phos": alk_phos, "ast": ast,
        "trig": trig, "platelet": platelet, "protime": protime, "stage": stage,
    }.items():
        if val is not None:
            payload[key] = float(val)

    payload_sig = json.dumps(payload, sort_keys=True)
    rapid_duplicate = (
        payload_sig == st.session_state.get("last_payload_sig")
        and time.time() - st.session_state.get("last_success_ts", 0.0) < SUBMIT_DEDUPE_WINDOW_S
    )

    if not rapid_duplicate:
        st.session_state.pop("last_error", None)
        try:
            request_start = time.perf_counter()
            with st.spinner("Computing risk (may take ~30s if backend is waking up)..."):
                # Bumping timeout to 60s to accommodate Render free-tier cold starts
                r = requests.post(f"{BACKEND_URL}/predict", json=payload, timeout=60)
            if r.status_code == 422:
                st.session_state.pop("last_result", None)
                st.session_state["last_error"] = {
                    "title": "Validation error (422) — check input ranges and required fields.",
                    "detail": r.json(),
                }
            elif r.status_code == 503:
                st.session_state.pop("last_result", None)
                st.session_state["last_error"] = {
                    "title": "Model unavailable (503) — check backend /health.",
                    "detail": r.json(),
                }
            else:
                r.raise_for_status()
                st.session_state["last_result"] = r.json()
                st.session_state["last_latency_ms"] = (time.perf_counter() - request_start) * 1000
                st.session_state["last_payload_sig"] = payload_sig
                st.session_state["last_success_ts"] = time.time()
                st.session_state["history"] = fetch_history(
                    limit=st.session_state.get("history_limit", 10)
                )
        except requests.exceptions.Timeout:
            st.session_state.pop("last_result", None)
            st.session_state["last_error"] = {
                "title": (
                    "Backend timed out waking up (cold start). Render is spinning up — "
                    "please click 'Compute risk' again in a few seconds."
                ),
                "detail": None,
            }
        except requests.exceptions.ConnectionError:
            st.session_state.pop("last_result", None)
            st.session_state["last_error"] = {
                "title": f"Could not reach backend at {BACKEND_URL} — is it running?",
                "detail": None,
            }
        except Exception as e:
            st.session_state.pop("last_result", None)
            st.session_state["last_error"] = {
                "title": f"Request to backend failed: {e}",
                "detail": None,
            }

last_error = st.session_state.get("last_error")
if last_error is not None:
    st.error(last_error["title"])
    if last_error.get("detail") is not None:
        st.json(last_error["detail"])

data = st.session_state.get("last_result")
if data is not None:
    prob = data["probability"]
    st.metric("Estimated 5-year severe event risk", f"{prob:.1%}")
    st.caption("95% CI (OOF): ROC-AUC 0.8828 [0.8409, 0.9185] — Mayo Clinic PBC cohort")

    band = data.get("risk_band")
    if band:
        badge = {
            "low": ("Low", "#1b5e20", "#00d4aa"),
            "intermediate": ("Intermediate", "#7a4f00", "#ffb74d"),
            "high": ("High", "#7f1d1d", "#ff5252"),
        }[band]
        st.markdown(
            f"<span style='display:inline-block; padding:4px 16px; border-radius:20px; "
            f"font-weight:700; font-size:0.95em; color:{badge[2]}; "
            f"background:{badge[1]}; border:1px solid {badge[2]}40;'>"
            f"Risk band: {badge[0]}</span>",
            unsafe_allow_html=True,
        )

    latency_ms = st.session_state.get("last_latency_ms")
    if latency_ms is not None:
        version = data.get("model_version")
        version_suffix = f" · model {version}" if version else ""
        st.caption(f"Scored in {latency_ms:.0f} ms{version_suffix}")

    warnings = data.get("warnings") or []
    if warnings:
        st.warning("\n".join(warnings))

    contributions = data.get("contributions", [])
    with_impact = [c for c in contributions if c["impact"] is not None]
    if with_impact:
        with_impact.sort(key=lambda c: abs(c["impact"]), reverse=True)
        labels = [
            f"{DISPLAY_NAMES.get(c['feature'], c['feature'])}"
            + ("*" if c["imputed"] else "")
            for c in with_impact
        ]
        impacts = [c["impact"] for c in with_impact]
        colors = ["#ff5252" if i > 0 else "#00d4aa" for i in impacts]
        fig = go.Figure(go.Bar(x=impacts, y=labels, orientation="h", marker_color=colors))
        fig.update_layout(
            title_text="Feature contributions (SHAP, log-odds; red = raises risk)",
            xaxis_title="Impact on risk score",
            yaxis={"autorange": "reversed"},
            height=600,
        )
        st.plotly_chart(fig, width="stretch")
        st.caption("* imputed server-side (not provided in the request)")
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 16)
            pdf.cell(0, 10, "HepatiQ - Risk Assessment Report", ln=True, align="C")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 6, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", ln=True, align="C")
            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "Patient Inputs", ln=True)
            pdf.set_font("Helvetica", "", 10)
            for k, v in payload.items():
                if k in DISPLAY_NAMES:
                    pdf.cell(0, 6, f"  {DISPLAY_NAMES[k]}: {v}", ln=True)
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "Results", ln=True)
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 6, f"  5-year severe event risk: {prob:.1%}", ln=True)
            pdf.cell(0, 6, f"  Risk band: {band.capitalize()}", ln=True)
            pdf.cell(0, 6, f"  Model: {model_version}", ln=True)
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "Top Risk Contributors (SHAP)", ln=True)
            pdf.set_font("Helvetica", "", 9)
            top_contribs = sorted([c for c in contribs if c.get('impact') is not None], key=lambda x: abs(x['impact']), reverse=True)[:5]
            for c in top_contribs:
                name = DISPLAY_NAMES.get(c['feature'], c['feature'])
                imp = c['impact']
                pdf.cell(0, 5, f"  {name}: {imp:+.3f} ({'raises' if imp > 0 else 'lowers'} risk)", ln=True)
            pdf.ln(5)
            pdf.set_font("Helvetica", "I", 8)
            pdf.multi_cell(0, 4, "RESEARCH PROTOTYPE - Not a medical device or diagnostic tool. Not a substitute for physician judgment. See docs/LIMITATIONS.md for details.")
            pdf_bytes = pdf.output()
            st.download_button(
                label="Download PDF Report",
                data=bytes(pdf_bytes),
                file_name=f"hepatiq_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.caption(f"PDF export unavailable: {e}")
    else:
        st.info("No SHAP contributions available (explainer not ready — see /health).")

with st.expander("Recent predictions (local history)"):
    col_a, col_b, _ = st.columns([1, 1, 4])
    with col_a:
        limit = st.selectbox("Show", [10, 25, 50, 100], key="history_limit", format_func=lambda n: f"{n} most recent")
    with col_b:
        risk_filter = st.selectbox("Risk band", ['All', 'low', 'intermediate', 'high'], index=0)
    history = st.session_state.get("history")
    if history is None or history.get("limit") != limit or st.session_state.get("history_filter") != risk_filter:
        history = fetch_history(limit=limit, risk_band=risk_filter)
        st.session_state["history"] = history
        st.session_state["history_filter"] = risk_filter
    if st.button("Clear history"):
        try:
            dr = requests.delete(f"{BACKEND_URL}/history", timeout=10)
            dr.raise_for_status()
            history = fetch_history(limit=limit, risk_band=risk_filter)
            st.session_state["history"] = history
        except requests.exceptions.RequestException:
            st.caption("Could not clear history — backend unavailable.")
    if history["error"] is not None:
        st.caption(history["error"])
    elif not history["items"]:
        st.caption("No predictions logged yet.")
    else:
        try:
            import csv, io
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Time (UTC)', 'Risk', 'Risk Band'])
            for it in history["items"]:
                writer.writerow([it['created_at'], f"{it['probability']:.1%}", _risk_band(it['probability'])])
            st.download_button('Download CSV', output.getvalue(), file_name='hepatiq_history.csv', mime='text/csv')
        except Exception:
            pass
        rows = []
        for it in history["items"]:
            top = sorted(
                (c for c in it["contributions"] if c["impact"] is not None),
                key=lambda c: abs(c["impact"]),
                reverse=True,
            )[:3]
            rows.append({
                "Time (UTC)": it["created_at"],
                "Risk": f"{it['probability']:.1%}",
                "Risk Band": _risk_band(it['probability']),
                "Top contributors": ", ".join(
                    f"{DISPLAY_NAMES.get(c['feature'], c['feature'])} ({c['impact']:+.2f})"
                    for c in top
                ),
            })
        st.dataframe(rows, width="stretch", hide_index=True)

st.divider()
with st.expander("Model Comparison"):
    st.markdown("""
| Model | ROC-AUC (CV) | Precision | Recall | F1 Score | Brier Score |
| --- | ---: | ---: | ---: | ---: | ---: |
| **Logistic Regression** (Selected) | 0.8800 | 0.7675 | 0.8105 | 0.7861 | 0.1363 |
| Random Forest | 0.8844 | 0.7235 | 0.8256 | 0.7694 | 0.1419 |
| XGBoost | 0.8706 | 0.7225 | 0.7508 | 0.1528 | 0.1528 |
""")
    st.caption("Logistic Regression chosen for superior calibration and interpretability.")
st.caption(
    "Research prototype — not a medical device or diagnostic tool. "
    "Model scope, calibration, and limits: docs/LIMITATIONS.md."
)
