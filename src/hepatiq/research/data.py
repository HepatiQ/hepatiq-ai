"""Canonical cohort loading for the frozen research audit.

Only the external 418-patient file is read. The interim imputed artifacts are
full-cohort transformations and must never enter a cross-validation path.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

from hepatiq.data.schema import validate_pbc
from hepatiq.ml.impute_pipeline import build_feature_frame
from hepatiq.paths import EXTERNAL_PBC
from hepatiq.research.config import (
    ALL_FEATURES,
    EXPECTED_COHORT_SIZE,
    EXPECTED_DROPPED_CENSORED,
    EXPECTED_EVENT_COUNT,
    EXPECTED_NON_EVENT_COUNT,
    FIVE_YEAR_DAYS,
    ID_COLUMN,
    LEAKY_COLUMNS,
    N_FOLDS,
    PRIMARY_SEED,
    TARGET_COLUMN,
)


@dataclass(frozen=True)
class ResearchCohort:
    frame: pd.DataFrame
    features: pd.DataFrame
    target: pd.Series
    ids: pd.Series

    @property
    def n(self) -> int:
        return len(self.target)

    @property
    def n_events(self) -> int:
        return int(self.target.sum())


def five_year_labels(frame: pd.DataFrame) -> pd.Series:
    """Return 1/0/NaN using the training definition, independent of row order."""
    if not {"time", "status"}.issubset(frame.columns):
        raise ValueError("cohort must contain time and status")

    labels = pd.Series(np.nan, index=frame.index, dtype=float)
    labels.loc[frame["time"] >= FIVE_YEAR_DAYS] = 0.0
    event_before = (frame["time"] < FIVE_YEAR_DAYS) & frame["status"].isin([1, 2])
    labels.loc[event_before] = 1.0
    return labels


def assert_no_leaky_columns(features: pd.DataFrame) -> None:
    leaked = sorted(set(features.columns).intersection(LEAKY_COLUMNS))
    if leaked:
        raise ValueError(f"leaky columns present in feature frame: {leaked}")


def assert_protocol_cohort(cohort: ResearchCohort) -> None:
    expected = (EXPECTED_COHORT_SIZE, EXPECTED_EVENT_COUNT, EXPECTED_NON_EVENT_COUNT)
    observed = (cohort.n, cohort.n_events, cohort.n - cohort.n_events)
    if observed != expected:
        raise ValueError(f"protocol cohort mismatch: observed {observed}, expected {expected}")


def load_research_cohort(path: str | Path = EXTERNAL_PBC) -> ResearchCohort:
    """Load, validate, label and split the canonical 418-patient cohort."""
    frame = pd.read_csv(path)
    validate_pbc(frame)

    labeled = frame.copy()
    labeled[TARGET_COLUMN] = five_year_labels(labeled)
    dropped = int(labeled[TARGET_COLUMN].isna().sum())
    if dropped != EXPECTED_DROPPED_CENSORED:
        raise ValueError(f"expected {EXPECTED_DROPPED_CENSORED} censored drops, got {dropped}")

    labeled = labeled.dropna(subset=[TARGET_COLUMN]).copy()
    labeled[TARGET_COLUMN] = labeled[TARGET_COLUMN].astype(int)

    features, ids, target = build_feature_frame(labeled)
    assert_no_leaky_columns(features)
    if tuple(features.columns) != ALL_FEATURES:
        raise ValueError(f"unexpected feature order: {tuple(features.columns)}")

    cohort = ResearchCohort(frame=labeled, features=features, target=target, ids=ids)
    assert_protocol_cohort(cohort)
    return cohort


def select_features(features: pd.DataFrame, names: tuple[str, ...]) -> pd.DataFrame:
    if len(set(names)) != len(names):
        raise ValueError("feature names must be unique")
    leaked = sorted(set(names).intersection(LEAKY_COLUMNS))
    if leaked:
        raise ValueError(f"leaky features requested: {leaked}")
    unknown = sorted(set(names) - set(ALL_FEATURES))
    if unknown:
        raise ValueError(f"unknown features requested: {unknown}")
    return features.loc[:, list(names)].copy()


def stratified_folds(
    target: pd.Series,
    *,
    n_folds: int = N_FOLDS,
    seed: int = PRIMARY_SEED,
) -> list[tuple[np.ndarray, np.ndarray]]:
    cv = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=seed)
    return [(train, test) for train, test in cv.split(np.zeros(len(target)), target)]


def fold_assignments(target: pd.Series, *, n_folds: int = N_FOLDS, seed: int = PRIMARY_SEED) -> np.ndarray:
    assignments = np.full(len(target), -1, dtype=int)
    for fold, (_, test) in enumerate(stratified_folds(target, n_folds=n_folds, seed=seed)):
        assignments[test] = fold
    if (assignments < 0).any():
        raise ValueError("not every patient received a fold assignment")
    return assignments


def heldout_indices(frame: pd.DataFrame) -> tuple[pd.Index, pd.Index]:
    """Return labeled derivation (randomized) and validation (non-randomized) ids."""
    derivation = frame.index[frame["trt"].notna()]
    validation = frame.index[frame["trt"].isna()]
    if set(derivation).intersection(validation):
        raise ValueError("derivation and validation sets overlap")
    return derivation, validation


def cohort_summary(cohort: ResearchCohort) -> dict:
    return {
        "n": cohort.n,
        "events": cohort.n_events,
        "nonevents": cohort.n - cohort.n_events,
        "event_rate": round(float(cohort.target.mean()), 4),
        "features": list(cohort.features.columns),
        "ids": int(cohort.ids.nunique()),
        "id_column": ID_COLUMN,
        "target": TARGET_COLUMN,
    }
