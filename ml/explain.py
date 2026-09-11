"""Explain a single patient's predicted risk using SHAP.

Loads the winning pipeline from models/model.pkl and shows which features
pushed one patient's predicted 5-year severe-event risk up or down.

Uses build_feature_frame() from impute_pipeline.py -- the same function
train.py uses -- so the feature columns and encoding here are guaranteed to
match what the model was actually trained on, rather than a hand-copied
re-implementation that could quietly drift out of sync later.

Note on explainer choice: shap.LinearExplainer only works because the
current winner (models/model.pkl) is Logistic Regression, which exposes
linear coefficients. If train.py is re-run and a tree-based model (Random
Forest / XGBoost) wins instead, this script needs shap.TreeExplainer
instead -- LinearExplainer will raise an error on a non-linear model. The
check below fails loudly rather than silently producing wrong output.

Run:
    python ml/explain.py
"""

import sys

import joblib
import pandas as pd
import shap
from sklearn.linear_model import LogisticRegression

from impute_pipeline import build_feature_frame

MODEL_PATH = "models/model.pkl"
DATA_PATH = "data/pbc_5yr_target.csv"
BACKGROUND_SAMPLE_SIZE = 100
RANDOM_STATE = 42


def main(patient_idx: int = 0):
    pipeline = joblib.load(MODEL_PATH)
    df = pd.read_csv(DATA_PATH)
    features, ids, target = build_feature_frame(df)

    # pipeline steps are named ("imputer", "scaler", "clf") in train.py --
    # NOT "classifier". Using the wrong key raises a clear KeyError rather
    # than silently explaining the wrong thing.
    classifier = pipeline.named_steps["clf"]
    preprocessor = pipeline[:-1]  # imputer + scaler only

    if not isinstance(classifier, LogisticRegression):
        sys.exit(
            f"models/model.pkl's classifier is {type(classifier).__name__}, not "
            "LogisticRegression. shap.LinearExplainer won't work on a "
            "non-linear model -- switch to shap.TreeExplainer(classifier) "
            "for Random Forest / XGBoost instead."
        )

    patient = features.iloc[[patient_idx]]
    patient_id = ids.iloc[patient_idx]
    actual_label = target.iloc[patient_idx]

    risk = pipeline.predict_proba(patient)[0][1]
    print(f"Patient id={patient_id} -- predicted 5-year severe event risk: {risk:.1%}")
    print(f"(actual observed label in the training data: {actual_label})")

    background = preprocessor.transform(features.sample(BACKGROUND_SAMPLE_SIZE, random_state=RANDOM_STATE))
    patient_transformed = preprocessor.transform(patient)

    explainer = shap.LinearExplainer(classifier, background)
    shap_values = explainer.shap_values(patient_transformed)

    contributions = pd.DataFrame({
        "feature": features.columns,
        "patient_value": patient.iloc[0].values,
        "impact": shap_values[0],
    }).sort_values("impact", key=abs, ascending=False)

    print("\nTop contributors to this patient's risk score:")
    for _, row in contributions.head(5).iterrows():
        sign = "+" if row["impact"] > 0 else "-"
        print(f"  {sign} {row['feature']:<10} (value={row['patient_value']})  impact={row['impact']:.3f}")


if __name__ == "__main__":
    main()