"""Impute missing lab values and scale features for the PBC 5-year cohort.

Why IterativeImputer (MICE) instead of mean/median fill:
    Liver lab values are correlated with each other (e.g. bilirubin, albumin,
    and copper all move together as liver function declines). Mean-imputation
    would ignore that and just plug in the same average value for every
    patient regardless of their other labs. IterativeImputer instead models
    each missing column as a function of the OTHER columns (a small regression
    per column), and repeats this a few times so the estimates refine each
    other. It's slower than mean-fill but uses the information you actually
    have instead of throwing it away.

Why time/status are dropped here (not just "not used"):
    severe_event_5yr was derived directly from time + status. Leaving them
    in as features would let the model "cheat" by reading the answer off
    the columns it was trained to predict, instead of learning the real
    relationship between labs/symptoms and outcome. At real prediction time
    for a new patient, you won't know their future time/status anyway.

Run:
    python ml/impute_pipeline.py

Input:  data/pbc_5yr_target.csv
Output: data/pbc_imputed.csv         (imputed, unscaled — human-readable)
        data/pbc_imputed_scaled.csv  (imputed + standardized — model-ready)
"""

import os
import pandas as pd
from sklearn.experimental import enable_iterative_imputer  # noqa: F401 (required to unlock IterativeImputer)
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler

INPUT_PATH = os.path.join("data", "pbc_5yr_target.csv")
IMPUTED_PATH = os.path.join("data", "pbc_imputed.csv")
IMPUTED_SCALED_PATH = os.path.join("data", "pbc_imputed_scaled.csv")

LEAKY_COLS = ["time", "status"]          # derived-from columns: must not be features
ID_COL = "id"                             # identifier: keep for reference, never impute/scale
TARGET_COL = "severe_event_5yr"           # label: keep as-is, never impute/scale


def load_cohort(path: str = INPUT_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing_expected = {ID_COL, TARGET_COL, *LEAKY_COLS} - set(df.columns)
    if missing_expected:
        raise ValueError(f"pbc_5yr_target.csv is missing expected columns: {missing_expected}")
    return df


def build_feature_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Split into (features, id, target), dropping leaky columns."""
    ids = df[ID_COL]
    target = df[TARGET_COL]
    features = df.drop(columns=[ID_COL, TARGET_COL, *LEAKY_COLS])

    # sex is text ('f'/'m'); encode to 0/1 so the imputer/scaler can use it
    features["sex"] = features["sex"].astype(str).str.lower().map({"f": 0, "m": 1})

    return features, ids, target


def impute(features: pd.DataFrame) -> pd.DataFrame:
    print("Missing values BEFORE imputation:")
    print(features.isnull().sum()[features.isnull().sum() > 0])
    print()

    imputer = IterativeImputer(random_state=42, max_iter=10)
    imputed_array = imputer.fit_transform(features)
    imputed_df = pd.DataFrame(imputed_array, columns=features.columns, index=features.index)

    print("Missing values AFTER imputation:", int(imputed_df.isnull().sum().sum()))
    return imputed_df


def scale(imputed_df: pd.DataFrame) -> pd.DataFrame:
    scaler = StandardScaler()
    scaled_array = scaler.fit_transform(imputed_df)
    return pd.DataFrame(scaled_array, columns=imputed_df.columns, index=imputed_df.index)


if __name__ == "__main__":
    raw = load_cohort()
    feats, ids, target = build_feature_frame(raw)

    imputed = impute(feats)
    imputed_out = pd.concat([ids, imputed, target], axis=1)
    imputed_out.to_csv(IMPUTED_PATH, index=False)
    print(f"\nSaved unscaled imputed cohort to {IMPUTED_PATH}")

    scaled = scale(imputed)
    scaled_out = pd.concat([ids, scaled, target], axis=1)
    scaled_out.to_csv(IMPUTED_SCALED_PATH, index=False)
    print(f"Saved imputed + scaled cohort to {IMPUTED_SCALED_PATH}")

    print(f"\nFinal feature matrix shape: {imputed.shape[0]} rows x {imputed.shape[1]} features")
    print(f"Features used: {list(imputed.columns)}")