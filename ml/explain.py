import joblib
import pandas as pd
import shap
import os

# 1. Load the winning pipeline and dataset
pipeline = joblib.load("models/model.pkl")
df = pd.read_csv("data/pbc_5yr_target.csv")

# 2. Prep the data exactly as we did in training
LEAKY_COLS = ["time", "status"]
df = df.drop(columns=[c for c in LEAKY_COLS if c in df.columns])
df["sex"] = df["sex"].astype(str).str.lower().map({"f": 0, "m": 1})
X = df.drop(columns=["id", "severe_event_5yr"])

# 3. Select a single patient for the demonstration (e.g., Patient #1)
patient_data = X.iloc[[0]]

# 4. Generate the 5-Year Risk Prediction
# predict_proba returns [[prob_class_0, prob_class_1]]
risk_prob = pipeline.predict_proba(patient_data)[0][1]
print(f"Patient 5-Year Severe Event Risk: {risk_prob:.1%}\n")

# 5. SHAP Explainability Extraction
# To explain a pipeline, we split the preprocessing steps from the classifier
preprocessor = pipeline[:-1]  # Imputer + Scaler
classifier = pipeline.named_steps['clf']

# Transform a background dataset (for SHAP baselines) and the specific patient
X_background = preprocessor.transform(X.sample(100, random_state=42))
patient_transformed = preprocessor.transform(patient_data)

# Calculate SHAP values using the LinearExplainer (ideal for Logistic Regression)
explainer = shap.LinearExplainer(classifier, X_background)
shap_values = explainer.shap_values(patient_transformed)

# 6. Display the Top Contributors
contributions = pd.DataFrame({
    "Feature": X.columns,
    "Patient Value": patient_data.iloc[0].values,
    "Impact": shap_values[0]
}).sort_values(by="Impact", ascending=False, key=abs)

print("Top Risk Contributors:")
for _, row in contributions.head(5).iterrows():
    sign = "+" if row["Impact"] > 0 else "-"
    print(f" {sign} {row['Feature']:<10} (Value: {row['Patient Value']:<5}) -> Impact: {row['Impact']:.3f}")