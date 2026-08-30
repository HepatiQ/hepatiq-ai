"""Minimal training script that creates a toy model for local development and saves it to models/model.pkl

Run this to generate a pipeline compatible with backend/main.py.
"""

import numpy as np
import pandas as pd
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import joblib
import os


def generate_dummy_data(n=500):
    rng = np.random.RandomState(0)
    bilirubin = rng.lognormal(mean=0.0, sigma=0.5, size=n)
    albumin = rng.normal(loc=3.5, scale=0.4, size=n)
    age = rng.normal(loc=60, scale=12, size=n)
    prothrombin = rng.normal(loc=12, scale=1.5, size=n)
    platelets = rng.normal(loc=200000, scale=50000, size=n)

    # synthetic outcome for demo purposes
    logit = 0.5 * bilirubin - 0.8 * albumin + 0.02 * age + 0.03 * prothrombin - 0.00001 * platelets
    prob = 1.0 / (1.0 + np.exp(-logit))
    y = (np.random.rand(n) < prob).astype(int)

    df = pd.DataFrame({
        "bilirubin": bilirubin,
        "albumin": albumin,
        "age": age,
        "prothrombin_time": prothrombin,
        "platelets": platelets,
        "outcome": y,
    })
    return df


def train_and_save(path="models/model.pkl"):
    df = generate_dummy_data()
    X = df[["bilirubin", "albumin", "age", "prothrombin_time", "platelets"]].values
    y = df["outcome"].values

    pipeline = Pipeline([
        ("imputer", IterativeImputer(random_state=0)),
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, solver="lbfgs")),
    ])

    pipeline.fit(X, y)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(pipeline, path)
    print(f"Saved model to {path}")


if __name__ == "__main__":
    train_and_save()
