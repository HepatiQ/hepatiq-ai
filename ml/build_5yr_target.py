"""Construct the 5-year severe event target from the raw Mayo Clinic PBC dataset.

Definition (per README "Scope & Limitations" and "Dataset & Attribution"):
    severe_event_5yr = 1  if the patient had a transplant (status==1) or died
                           (status==2) within 1,825 days (5 years) of baseline
    severe_event_5yr = 0  if the patient survived event-free through the
                           5-year mark (time >= 1825), regardless of what
                           eventually happened to them or their status
    dropped            if the patient was censored (status==0) before the
                           5-year mark — their 5-year outcome is unknown

Run:
    python ml/build_5yr_target.py

Input:  data/pbc.csv
Output: data/pbc_5yr_target.csv
"""

import os
import pandas as pd  # pyright: ignore[reportMissingModuleSource]

FIVE_YEAR_DAYS = 1825
INPUT_PATH = os.path.join("data", "pbc.csv")
OUTPUT_PATH = os.path.join("data", "pbc_5yr_target.csv")


def label_severe_event(row: pd.Series) -> float:
    """Return 1.0, 0.0, or None (drop) for a single patient row."""
    if row["time"] >= FIVE_YEAR_DAYS:
        return 0.0
    if row["status"] in (1, 2):
        return 1.0
    return None  # censored (status==0) before 5 years: unknown outcome, drop


def build_target(input_path: str = INPUT_PATH) -> pd.DataFrame:
    df = pd.read_csv(input_path)

    required_cols = {"time", "status"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"pbc.csv is missing expected columns: {missing}")

    df["severe_event_5yr"] = df.apply(label_severe_event, axis=1)

    n_total = len(df)
    n_dropped = df["severe_event_5yr"].isnull().sum()

    df = df.dropna(subset=["severe_event_5yr"]).copy()
    df["severe_event_5yr"] = df["severe_event_5yr"].astype(int)

    print(f"Total records loaded:        {n_total}")
    print(f"Dropped (censored, <5yr):    {n_dropped}")
    print(f"Kept (labeled cohort):       {len(df)}")
    print()
    print("Class balance:")
    print(df["severe_event_5yr"].value_counts().rename({0: "event-free", 1: "severe_event"}))
    print(df["severe_event_5yr"].value_counts(normalize=True).round(3).rename({0: "event-free", 1: "severe_event"}))

    return df


if __name__ == "__main__":
    labeled_df = build_target()
    labeled_df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved labeled cohort to {OUTPUT_PATH}")