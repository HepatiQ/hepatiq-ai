import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(page_title="HepatiQ", layout="wide")
st.title("HepatiQ — 5-Year Severe Event Risk Calculator")
st.write(
    "Enter patient data and press 'Compute risk' to call the backend API. "
    "Age, sex, edema, bilirubin, and albumin are required; optional fields left "
    "blank are imputed server-side by the model's IterativeImputer."
)

DISPLAY_NAMES = {
    "trt": "Treatment", "age": "Age", "sex": "Sex", "ascites": "Ascites",
    "hepato": "Hepatomegaly", "spiders": "Spiders", "edema": "Edema",
    "bili": "Bilirubin", "chol": "Cholesterol", "albumin": "Albumin",
    "copper": "Copper", "alk.phos": "Alk. Phos", "ast": "AST",
    "trig": "Triglycerides", "platelet": "Platelet", "protime": "Protime",
    "stage": "Stage",
}


def optional_number(label, min_value, max_value, format):
    return st.number_input(
        label, min_value=min_value, max_value=max_value, value=None, format=format
    )


with st.form("input_form"):
    st.subheader("Required")
    c1, c2, c3 = st.columns(3)
    with c1:
        age = st.number_input("Age (years)", min_value=0.0, max_value=120.0, value=55.0, format="%.1f")
    with c2:
        sex = st.selectbox("Sex", options=["f", "m"], index=0)
    with c3:
        edema = st.selectbox("Edema (0, 0.5, 1)", options=[0.0, 0.5, 1.0], index=0)
    c1, c2 = st.columns(2)
    with c1:
        bili = st.number_input("Bilirubin (mg/dL)", min_value=0.0, max_value=100.0, value=1.0, format="%.2f")
    with c2:
        albumin = st.number_input("Albumin (g/dL)", min_value=0.0, max_value=10.0, value=3.5, format="%.2f")

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
        chol = optional_number("Cholesterol (mg/dL)", 0.0, 5000.0, "%.1f")
    with c2:
        copper = optional_number("Urine copper (ug/day)", 0.0, 1000.0, "%.1f")
    with c3:
        alk_phos = optional_number("Alk. Phos (U/L)", 0.0, 50000.0, "%.1f")
    with c4:
        ast = optional_number("AST (U/L)", 0.0, 10000.0, "%.2f")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        trig = optional_number("Triglycerides (mg/dL)", 0.0, 10000.0, "%.1f")
    with c2:
        platelet = optional_number("Platelets (thousands/uL)", 1.0, 1000.0, "%.0f")
    with c3:
        protime = optional_number("Prothrombin time (sec)", 1.0, 100.0, "%.1f")
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

    try:
        r = requests.post("http://localhost:8000/predict", json=payload, timeout=30)
        if r.status_code == 422:
            st.error("Validation error (422) — check input ranges and required fields.")
            st.json(r.json())
            st.stop()
        if r.status_code == 503:
            st.error("Model unavailable (503) — check backend /health.")
            st.json(r.json())
            st.stop()
        r.raise_for_status()
        data = r.json()

        prob = data["probability"]
        st.metric("Estimated 5-year severe event risk", f"{prob:.1%}")

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
            colors = ["indianred" if i > 0 else "steelblue" for i in impacts]
            fig = go.Figure(go.Bar(x=impacts, y=labels, orientation="h", marker_color=colors))
            fig.update_layout(
                title_text="Feature contributions (SHAP, log-odds; red = raises risk)",
                xaxis_title="Impact on risk score",
                yaxis={"autorange": "reversed"},
                height=600,
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("* imputed server-side (not provided in the request)")
        else:
            st.info("No SHAP contributions available (explainer not ready — see /health).")

    except requests.exceptions.ConnectionError:
        st.error("Could not reach backend at http://localhost:8000 — is it running?")
    except Exception as e:
        st.error(f"Request to backend failed: {e}")

with st.expander("Recent predictions (local history)"):
    try:
        hr = requests.get("http://localhost:8000/history", params={"limit": 10}, timeout=5)
        if hr.status_code == 200:
            items = hr.json().get("items", [])
            if items:
                rows = []
                for it in items:
                    top = sorted(
                        (c for c in it["contributions"] if c["impact"] is not None),
                        key=lambda c: abs(c["impact"]),
                        reverse=True,
                    )[:3]
                    rows.append({
                        "Time (UTC)": it["created_at"],
                        "Risk": f"{it['probability']:.1%}",
                        "Top contributors": ", ".join(
                            f"{DISPLAY_NAMES.get(c['feature'], c['feature'])} ({c['impact']:+.2f})"
                            for c in top
                        ),
                    })
                st.dataframe(rows, use_container_width=True, hide_index=True)
            else:
                st.caption("No predictions logged yet.")
        else:
            st.caption(f"History unavailable (HTTP {hr.status_code}).")
    except requests.exceptions.ConnectionError:
        st.caption("Backend not reachable — history hidden.")
