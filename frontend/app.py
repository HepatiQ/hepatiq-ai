import streamlit as st
import requests
import plotly.graph_objects as go

st.set_page_config(page_title="HepatiQ demo", layout="centered")
st.title("HepatiQ — PBC mortality risk (demo)")
st.write("Enter the five routine inputs and press 'Compute risk' to call the backend API.")

with st.form("input_form"):
    bilirubin = st.number_input("Bilirubin (mg/dL)", min_value=0.0, value=1.0, format="%.3f")
    albumin = st.number_input("Albumin (g/dL)", min_value=0.0, value=3.5, format="%.3f")
    age = st.number_input("Age (years)", min_value=0.0, value=60.0, format="%.1f")
    prothrombin_time = st.number_input("Prothrombin Time (sec)", min_value=0.0, value=12.0, format="%.2f")
    platelets = st.number_input("Platelets (per µL)", min_value=0.0, value=200000.0, format="%.0f")
    submitted = st.form_submit_button("Compute risk")

if submitted:
    payload = {
        "bilirubin": float(bilirubin),
        "albumin": float(albumin),
        "age": float(age),
        "prothrombin_time": float(prothrombin_time),
        "platelets": float(platelets),
    }
    try:
        r = requests.post("http://localhost:8000/predict", json=payload, timeout=5)
        r.raise_for_status()
        data = r.json()

        prob = data.get("probability")
        st.metric("Estimated mortality probability", f"{prob:.3f}")

        shap_vals = data.get("shap_values", [])
        if shap_vals and len(shap_vals) == 5:
            features = ["Bilirubin", "Albumin", "Age", "Prothrombin Time", "Platelets"]
            fig = go.Figure(go.Bar(x=features, y=shap_vals, marker_color='indianred'))
            fig.update_layout(title_text="SHAP values (feature contributions)", yaxis_title="SHAP value")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No SHAP values returned (model_loaded={data.get('model_loaded')})")

    except Exception as e:
        st.error(f"Request to backend failed: {e}")
