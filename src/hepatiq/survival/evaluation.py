"""Leakage-controlled evaluation for the v2 survival baseline.

The survival model is compared with the v1 binary classifier on the same
out-of-fold rows. The v1 baseline is refit inside each fold on only the rows
whose 5-year label is known, then scored on every test row. That keeps the
comparison honest even though censored patients cannot contribute a 5-year
binary label.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

from hepatiq.ml.train import build_pipelines
from hepatiq.research.config import ALL_FEATURES, N_BOOTSTRAP
from hepatiq.research.metrics import (
    auc_score,
    brier_score,
    calibration_in_the_large,
    calibration_slope_intercept,
    expected_calibration_error,
)
from hepatiq.research.metrics import (
    bootstrap_ci as probability_bootstrap_ci,
)
from hepatiq.risk.benchmark import five_year_outcome
from hepatiq.risk.metrics import bootstrap_ci as c_index_bootstrap_ci
from hepatiq.risk.metrics import harrell_c_index
from hepatiq.survival.model import (
    HORIZON_DAYS,
    MIN_MEANINGFUL_DELTA_C,
    N_FOLDS,
    PRIMARY_SEED,
    absolute_risk_at_horizon,
    breslow_cumulative_hazard,
    fit_survival_model,
    survival_feature_frame,
    survival_labels,
)

V1_FEATURES = tuple(ALL_FEATURES)


@dataclass(frozen=True)
class CrossValidationResult:
    name: str
    oof_hazard_ratio: np.ndarray | None
    oof_risk_5y: np.ndarray
    fold_c_index: tuple[float, ...]
    fold_auc_5y: tuple[float, ...]
    fold_brier_5y: tuple[float, ...]


def _stratified_folds(event: np.ndarray, n_splits: int, seed: int):
    if n_splits < 2:
        raise ValueError("n_splits must be at least 2")
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    return list(cv.split(np.zeros(len(event)), event))


def _five_year_known(labels: np.ndarray) -> np.ndarray:
    known = np.isfinite(labels)
    if known.sum() < 2:
        raise ValueError("five-year evaluation requires at least two known labels")
    return known


def _binary_metrics(labels: np.ndarray, risk: np.ndarray) -> tuple[float, float]:
    known = _five_year_known(labels)
    y = labels[known]
    p = risk[known]
    if len(np.unique(y)) < 2:
        return float("nan"), float("nan")
    return float(roc_auc_score(y, p)), float(np.mean((p - y) ** 2))


def cross_validate_survival(
    cohort: pd.DataFrame,
    *,
    n_splits: int = N_FOLDS,
    seed: int = PRIMARY_SEED,
    horizon: int = HORIZON_DAYS,
) -> CrossValidationResult:
    """Fit the Cox model out-of-fold and return absolute 5-year risks."""
    features = survival_feature_frame(cohort)
    duration, event = survival_labels(cohort)
    labels = five_year_outcome(duration, event, horizon=horizon)

    oof_hazard = np.full(len(cohort), np.nan)
    oof_risk = np.full(len(cohort), np.nan)
    fold_c: list[float] = []
    fold_auc: list[float] = []
    fold_brier: list[float] = []

    for fold, (train, test) in enumerate(_stratified_folds(event, n_splits, seed)):
        model = fit_survival_model(
            features.iloc[train],
            duration[train],
            event[train],
            seed=seed + fold,
        )
        train_hazard = model.predict_hazard_ratio(features.iloc[train])
        test_hazard = model.predict_hazard_ratio(features.iloc[test])
        baseline_hazard = breslow_cumulative_hazard(
            duration[train],
            event[train],
            train_hazard,
            horizon=horizon,
        )
        test_risk = absolute_risk_at_horizon(
            test_hazard,
            baseline_hazard,
            horizon=horizon,
        )

        oof_hazard[test] = test_hazard
        oof_risk[test] = test_risk
        fold_c.append(float(harrell_c_index(duration[test], event[test], test_risk)))
        auc, brier = _binary_metrics(labels[test], test_risk)
        fold_auc.append(auc)
        fold_brier.append(brier)

    if not np.isfinite(oof_hazard).all() or not np.isfinite(oof_risk).all():
        raise ValueError("cross-validation did not produce complete out-of-fold predictions")
    return CrossValidationResult(
        name="XGBoost Cox",
        oof_hazard_ratio=oof_hazard,
        oof_risk_5y=oof_risk,
        fold_c_index=tuple(fold_c),
        fold_auc_5y=tuple(fold_auc),
        fold_brier_5y=tuple(fold_brier),
    )


def cross_validate_v1_baseline(
    cohort: pd.DataFrame,
    *,
    n_splits: int = N_FOLDS,
    seed: int = PRIMARY_SEED,
    horizon: int = HORIZON_DAYS,
) -> CrossValidationResult:
    """Refit the v1 logistic pipeline out-of-fold on known 5-year labels."""
    missing = sorted(set(V1_FEATURES) - set(cohort.columns))
    if missing:
        raise ValueError(f"cohort is missing v1 features: {missing}")

    features = cohort.loc[:, list(V1_FEATURES)].copy()
    features["sex"] = features["sex"].astype(str).str.lower().map({"f": 0.0, "m": 1.0})
    if features["sex"].isna().any():
        raise ValueError("sex must contain only 'f' and 'm'")

    duration, event = survival_labels(cohort)
    labels = five_year_outcome(duration, event, horizon=horizon)
    known = _five_year_known(labels)

    oof_risk = np.full(len(cohort), np.nan)
    fold_c: list[float] = []
    fold_auc: list[float] = []
    fold_brier: list[float] = []

    for train, test in _stratified_folds(event, n_splits, seed):
        train_known = train[known[train]]
        y_train = labels[train_known].astype(int)
        if len(np.unique(y_train)) < 2:
            raise ValueError("training fold has only one 5-year class")
        positive_weight = float((y_train == 0).sum() / (y_train == 1).sum())
        pipeline = build_pipelines(positive_weight)["logistic_regression"]
        pipeline.fit(features.iloc[train_known], y_train)

        test_risk = pipeline.predict_proba(features.iloc[test])[:, 1]
        oof_risk[test] = test_risk
        fold_c.append(float(harrell_c_index(duration[test], event[test], test_risk)))
        auc, brier = _binary_metrics(labels[test], test_risk)
        fold_auc.append(auc)
        fold_brier.append(brier)

    if not np.isfinite(oof_risk).all():
        raise ValueError("v1 baseline did not produce complete out-of-fold predictions")
    return CrossValidationResult(
        name="HepatiQ v1 logistic",
        oof_hazard_ratio=None,
        oof_risk_5y=oof_risk,
        fold_c_index=tuple(fold_c),
        fold_auc_5y=tuple(fold_auc),
        fold_brier_5y=tuple(fold_brier),
    )


def summarize_c_index(
    duration: np.ndarray,
    event: np.ndarray,
    risk: np.ndarray,
    *,
    n_boot: int = N_BOOTSTRAP,
    seed: int = PRIMARY_SEED,
) -> dict[str, float | int]:
    point = float(harrell_c_index(duration, event, risk))
    lower, upper = c_index_bootstrap_ci(
        lambda indices: harrell_c_index(duration[indices], event[indices], risk[indices]),
        len(risk),
        n_boot=n_boot,
        seed=seed,
    )
    return {
        "point": point,
        "lower": lower,
        "upper": upper,
        "n_boot": n_boot,
    }


def summarize_five_year(
    duration: np.ndarray,
    event: np.ndarray,
    risk: np.ndarray,
    *,
    horizon: int = HORIZON_DAYS,
    n_boot: int = N_BOOTSTRAP,
    seed: int = PRIMARY_SEED,
) -> dict[str, object]:
    labels = five_year_outcome(duration, event, horizon=horizon)
    known = _five_year_known(labels)
    y = labels[known]
    p = risk[known]
    slope, intercept = calibration_slope_intercept(y, p)
    return {
        "n": int(known.sum()),
        "events": int(y.sum()),
        "auc": probability_bootstrap_ci(y, p, auc_score, n_boot=n_boot, seed=seed),
        "brier": probability_bootstrap_ci(y, p, brier_score, n_boot=n_boot, seed=seed),
        "calibration_slope": slope,
        "calibration_intercept": intercept,
        "calibration_in_the_large": calibration_in_the_large(y, p),
        "ece": expected_calibration_error(y, p),
        "mean_predicted": float(p.mean()),
        "observed": float(y.mean()),
    }


def evaluate_survival_comparison(
    cohort: pd.DataFrame,
    *,
    survival_result: CrossValidationResult | None = None,
    baseline_result: CrossValidationResult | None = None,
    n_splits: int = N_FOLDS,
    seed: int = PRIMARY_SEED,
    horizon: int = HORIZON_DAYS,
    n_boot: int = N_BOOTSTRAP,
) -> dict[str, object]:
    """Evaluate both models out-of-fold and apply the predeclared promotion bar."""
    survival_result = survival_result or cross_validate_survival(
        cohort,
        n_splits=n_splits,
        seed=seed,
        horizon=horizon,
    )
    baseline_result = baseline_result or cross_validate_v1_baseline(
        cohort,
        n_splits=n_splits,
        seed=seed,
        horizon=horizon,
    )

    duration, event = survival_labels(cohort)
    survival_c = summarize_c_index(
        duration,
        event,
        survival_result.oof_risk_5y,
        n_boot=n_boot,
        seed=seed,
    )
    baseline_c = summarize_c_index(
        duration,
        event,
        baseline_result.oof_risk_5y,
        n_boot=n_boot,
        seed=seed,
    )
    delta_c = float(survival_c["point"]) - float(baseline_c["point"])
    promote = bool(delta_c >= MIN_MEANINGFUL_DELTA_C and survival_c["lower"] > baseline_c["point"])

    return {
        "cohort": {
            "rows": int(len(cohort)),
            "events": int(event.sum()),
            "censored": int((event == 0).sum()),
        },
        "cv": {
            "folds": n_splits,
            "seed": seed,
            "stratified_by": "event",
            "horizon_days": horizon,
        },
        "survival": {
            "model": survival_result.name,
            "c_index": survival_c,
            "five_year": summarize_five_year(
                duration,
                event,
                survival_result.oof_risk_5y,
                horizon=horizon,
                n_boot=n_boot,
                seed=seed,
            ),
            "fold_c_index": list(survival_result.fold_c_index),
            "fold_auc_5y": list(survival_result.fold_auc_5y),
            "fold_brier_5y": list(survival_result.fold_brier_5y),
        },
        "baseline": {
            "model": baseline_result.name,
            "c_index": baseline_c,
            "five_year": summarize_five_year(
                duration,
                event,
                baseline_result.oof_risk_5y,
                horizon=horizon,
                n_boot=n_boot,
                seed=seed,
            ),
            "fold_c_index": list(baseline_result.fold_c_index),
            "fold_auc_5y": list(baseline_result.fold_auc_5y),
            "fold_brier_5y": list(baseline_result.fold_brier_5y),
        },
        "comparison": {
            "delta_c_index": delta_c,
            "min_meaningful_delta_c": MIN_MEANINGFUL_DELTA_C,
            "promote_to_serving": promote,
            "criterion": (
                "pooled out-of-fold Harrell C-index must improve by at least "
                f"{MIN_MEANINGFUL_DELTA_C:.2f} over v1 and the survival 95% "
                "bootstrap lower bound must exceed the v1 point estimate"
            ),
        },
    }
