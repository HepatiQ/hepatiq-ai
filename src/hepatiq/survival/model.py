"""Censoring-aware survival baseline for the canonical PBC cohort.

The v1 product model is a 5-year binary classifier trained after dropping
patients censored before the horizon. This module keeps the full time-to-event
outcome and fits an XGBoost Cox proportional-hazards model (``survival:cox``).

Design choices:
- All 418 patients contribute; censored observations are encoded as negative
  durations, which is the XGBoost Cox convention.
- ``trt`` and ``randomized`` are not model features. Treatment is missing by
  design for the 106 non-randomized patients, so imputing it would turn cohort
  membership into a fake clinical predictor.
- Missing baseline labs are left as NaN and handled by XGBoost's native missing
  value support. No imputer is fitted before cross-validation.
- Hazard ratios are converted to absolute 5-year risk with a Breslow baseline
  cumulative hazard estimated from the training fold only.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from hepatiq.data.cohorts import SURVIVAL_DURATION_COLUMN, SURVIVAL_EVENT_COLUMN

HORIZON_DAYS = 1825
PRIMARY_SEED = 42
N_FOLDS = 5
MIN_MEANINGFUL_DELTA_C = 0.02

SURVIVAL_FEATURES = (
    "age",
    "sex",
    "ascites",
    "hepato",
    "spiders",
    "edema",
    "bili",
    "chol",
    "albumin",
    "copper",
    "alk.phos",
    "ast",
    "trig",
    "platelet",
    "protime",
    "stage",
)

LEAKY_COLUMNS = (
    "id",
    "time",
    "status",
    "futime",
    "day",
    "duration_days",
    "event",
    "event_type",
    "randomized",
    "trt",
)

MODEL_PARAMS = {
    "objective": "survival:cox",
    "n_estimators": 200,
    "max_depth": 2,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_lambda": 2.0,
    "reg_alpha": 0.5,
    "min_child_weight": 5,
    "n_jobs": 1,
    "verbosity": 0,
}


@dataclass(frozen=True)
class SurvivalModel:
    """Serializable model plus the feature contract used to fit it."""

    estimator: XGBRegressor
    feature_names: tuple[str, ...]

    def predict_hazard_ratio(self, features: pd.DataFrame) -> np.ndarray:
        return predict_hazard_ratio(self.estimator, features, self.feature_names)


def survival_feature_frame(cohort: pd.DataFrame) -> pd.DataFrame:
    """Return the 16-feature frame used by the survival model."""
    missing = sorted(set(SURVIVAL_FEATURES) - set(cohort.columns))
    if missing:
        raise ValueError(f"survival cohort is missing features: {missing}")

    features = cohort.loc[:, list(SURVIVAL_FEATURES)].copy()
    features["sex"] = features["sex"].astype(str).str.lower().map({"f": 0.0, "m": 1.0})
    if features["sex"].isna().any():
        raise ValueError("sex must contain only 'f' and 'm'")

    leaked = sorted(set(features.columns).intersection(LEAKY_COLUMNS))
    if leaked:
        raise ValueError(f"leaky columns present in survival feature frame: {leaked}")
    if tuple(features.columns) != SURVIVAL_FEATURES:
        raise ValueError(f"unexpected survival feature order: {tuple(features.columns)}")
    return features


def survival_labels(cohort: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Return (duration_days, event) arrays with the canonical contracts checked."""
    missing = sorted({SURVIVAL_DURATION_COLUMN, SURVIVAL_EVENT_COLUMN} - set(cohort.columns))
    if missing:
        raise ValueError(f"survival cohort is missing outcome columns: {missing}")

    duration = cohort[SURVIVAL_DURATION_COLUMN].to_numpy(dtype=float)
    event = cohort[SURVIVAL_EVENT_COLUMN].to_numpy(dtype=int)
    if not np.isfinite(duration).all() or (duration <= 0).any():
        raise ValueError("duration_days must be finite and positive")
    if not np.isin(event, [0, 1]).all():
        raise ValueError("event must contain only 0 and 1")
    return duration, event


def cox_labels(duration: np.ndarray, event: np.ndarray) -> np.ndarray:
    """XGBoost Cox convention: negative duration marks a right-censored row."""
    duration = np.asarray(duration, dtype=float)
    event = np.asarray(event).astype(bool)
    return np.where(event, duration, -duration)


def build_survival_model(*, seed: int = PRIMARY_SEED) -> XGBRegressor:
    """Create the shallow, regularized Cox model used by the research baseline."""
    return XGBRegressor(random_state=seed, **MODEL_PARAMS)


def fit_survival_model(
    features: pd.DataFrame,
    duration: np.ndarray,
    event: np.ndarray,
    *,
    seed: int = PRIMARY_SEED,
) -> SurvivalModel:
    """Fit a Cox model on raw features, preserving missing values for XGBoost."""
    if len(features) != len(duration) or len(features) != len(event):
        raise ValueError("features, duration and event must have the same length")
    duration = np.asarray(duration, dtype=float)
    event = np.asarray(event, dtype=int)
    if not np.isfinite(duration).all() or (duration <= 0).any():
        raise ValueError("duration must be finite and positive")
    if not np.isin(event, [0, 1]).all():
        raise ValueError("event must contain only 0 and 1")

    estimator = build_survival_model(seed=seed)
    estimator.fit(features, cox_labels(duration, event))
    return SurvivalModel(estimator=estimator, feature_names=tuple(features.columns))


def predict_hazard_ratio(
    estimator: XGBRegressor,
    features: pd.DataFrame,
    feature_names: tuple[str, ...] | None = None,
) -> np.ndarray:
    """Return relative hazard ratios, checked for a usable positive scale."""
    if feature_names is not None:
        if tuple(features.columns) != tuple(feature_names):
            raise ValueError("feature contract mismatch at prediction time")
    hazard = np.asarray(estimator.predict(features), dtype=float)
    if hazard.shape != (len(features),):
        raise ValueError("hazard ratio prediction has an unexpected shape")
    if not np.isfinite(hazard).all() or (hazard <= 0).any():
        raise ValueError("hazard ratios must be finite and positive")
    return hazard


def breslow_cumulative_hazard(
    duration: np.ndarray,
    event: np.ndarray,
    hazard_ratio: np.ndarray,
    *,
    horizon: int = HORIZON_DAYS,
) -> float:
    """Estimate baseline cumulative hazard at ``horizon`` using Breslow's method."""
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    duration = np.asarray(duration, dtype=float)
    event = np.asarray(event).astype(int)
    hazard_ratio = np.asarray(hazard_ratio, dtype=float)
    if not (len(duration) == len(event) == len(hazard_ratio)):
        raise ValueError("duration, event and hazard_ratio must have the same length")
    if not np.isfinite(duration).all() or (duration <= 0).any():
        raise ValueError("duration must be finite and positive")
    if not np.isin(event, [0, 1]).all():
        raise ValueError("event must contain only 0 and 1")
    if not np.isfinite(hazard_ratio).all() or (hazard_ratio <= 0).any():
        raise ValueError("hazard_ratio must be finite and positive")
    if not np.isfinite(horizon):
        raise ValueError("horizon must be finite")

    cumulative_hazard = 0.0
    event_times = np.unique(duration[(event == 1) & (duration <= horizon)])
    for event_time in event_times:
        deaths = int(np.sum((duration == event_time) & (event == 1)))
        at_risk = duration >= event_time
        risk_sum = float(hazard_ratio[at_risk].sum())
        if risk_sum <= 0:
            raise ValueError("risk set has no positive hazard mass")
        cumulative_hazard += deaths / risk_sum
    return cumulative_hazard


def absolute_risk_at_horizon(
    hazard_ratio: np.ndarray,
    baseline_cumulative_hazard: float,
    *,
    horizon: int = HORIZON_DAYS,
) -> np.ndarray:
    """Convert relative hazards to absolute event risk by the horizon."""
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    if not np.isfinite(baseline_cumulative_hazard) or baseline_cumulative_hazard < 0:
        raise ValueError("baseline_cumulative_hazard must be finite and non-negative")
    hazard_ratio = np.asarray(hazard_ratio, dtype=float)
    if not np.isfinite(hazard_ratio).all() or (hazard_ratio <= 0).any():
        raise ValueError("hazard_ratio must be finite and positive")

    survival = np.exp(-baseline_cumulative_hazard * hazard_ratio)
    risk = 1.0 - survival
    if (risk < 0).any() or (risk > 1).any():
        raise ValueError("absolute risk escaped [0, 1]")
    return risk
