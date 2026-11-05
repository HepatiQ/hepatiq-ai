"""Best-case, worst-case and death-only sensitivity for censored patients."""

from __future__ import annotations

import numpy as np
import pandas as pd

from hepatiq.research.config import FIVE_YEAR_DAYS
from hepatiq.research.data import five_year_labels


def labels_with_censoring(frame: pd.DataFrame, censored_label: int) -> pd.Series:
    if censored_label not in (0, 1):
        raise ValueError("censored_label must be 0 or 1")
    labels = five_year_labels(frame)
    labels = labels.fillna(float(censored_label)).astype(int)
    return labels.rename("severe_event_5yr")


def bound_summary(frame: pd.DataFrame) -> dict[str, object]:
    primary = five_year_labels(frame)
    censored = primary.isna()
    best = labels_with_censoring(frame, 0)
    worst = labels_with_censoring(frame, 1)
    return {
        "n_total": int(len(frame)),
        "labeled": int((~censored).sum()),
        "censored_before_5y": int(censored.sum()),
        "primary_events": int(primary.sum()),
        "primary_event_rate": float(primary.mean()),
        "best_case_events": int(best.sum()),
        "best_case_event_rate": float(best.mean()),
        "worst_case_events": int(worst.sum()),
        "worst_case_event_rate": float(worst.mean()),
    }


def death_only_labels(frame: pd.DataFrame) -> pd.Series:
    """Death within five years is the event; transplants and censoring are dropped."""
    if not {"time", "status"}.issubset(frame.columns):
        raise ValueError("frame must contain time and status")

    labels = pd.Series(np.nan, index=frame.index, dtype=float)
    labels.loc[frame["time"] >= FIVE_YEAR_DAYS] = 0.0
    died_before = (frame["time"] < FIVE_YEAR_DAYS) & (frame["status"] == 2)
    labels.loc[died_before] = 1.0
    return labels.rename("death_5yr")


def death_only_summary(frame: pd.DataFrame) -> dict[str, object]:
    labels = death_only_labels(frame)
    return {
        "n_labeled": int(labels.notna().sum()),
        "deaths": int(labels.sum()),
        "death_rate": float(labels.mean()),
        "dropped_transplant_or_censored": int(labels.isna().sum()),
    }
