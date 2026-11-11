"""Contract and leakage tests for the v2 Cox survival baseline."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from xgboost import XGBRegressor

from hepatiq.data import build_survival_cohort
from hepatiq.survival.evaluation import (
    cross_validate_survival,
    cross_validate_v1_baseline,
    evaluate_survival_comparison,
)
from hepatiq.survival.model import (
    HORIZON_DAYS,
    SURVIVAL_FEATURES,
    absolute_risk_at_horizon,
    breslow_cumulative_hazard,
    cox_labels,
    fit_survival_model,
    survival_feature_frame,
    survival_labels,
)


@pytest.fixture(scope="module")
def cohort() -> pd.DataFrame:
    return build_survival_cohort()


@pytest.fixture(scope="module")
def fitted_model(cohort: pd.DataFrame):
    features = survival_feature_frame(cohort)
    duration, event = survival_labels(cohort)
    return fit_survival_model(features, duration, event)


@pytest.fixture(scope="module")
def survival_cv(cohort: pd.DataFrame):
    return cross_validate_survival(cohort)


@pytest.fixture(scope="module")
def baseline_cv(cohort: pd.DataFrame):
    return cross_validate_v1_baseline(cohort)


@pytest.fixture(scope="module")
def comparison(cohort, survival_cv, baseline_cv):
    return evaluate_survival_comparison(
        cohort,
        survival_result=survival_cv,
        baseline_result=baseline_cv,
        n_boot=200,
    )


def test_feature_frame_excludes_outcome_and_treatment(cohort: pd.DataFrame) -> None:
    features = survival_feature_frame(cohort)

    assert tuple(features.columns) == SURVIVAL_FEATURES
    assert features.shape == (418, 16)
    assert not {"id", "trt", "randomized", "duration_days", "event", "time", "status"}.intersection(
        features.columns
    )
    assert set(features["sex"].unique()) == {0.0, 1.0}
    assert features.isna().any().any(), "missing labs must stay raw for XGBoost"


def test_survival_labels_preserve_censoring(cohort: pd.DataFrame) -> None:
    duration, event = survival_labels(cohort)
    labels = cox_labels(duration, event)

    assert duration.shape == event.shape == labels.shape == (418,)
    assert (labels[event == 1] > 0).all()
    assert (labels[event == 0] < 0).all()
    np.testing.assert_allclose(np.abs(labels), duration)


def test_breslow_cumulative_hazard_matches_hand_calculation() -> None:
    duration = np.array([1.0, 2.0, 3.0])
    event = np.array([1, 1, 0])
    hazard = np.ones(3)

    assert breslow_cumulative_hazard(duration, event, hazard, horizon=2) == pytest.approx(1 / 3 + 1 / 2)
    assert breslow_cumulative_hazard(duration, event, hazard, horizon=3) == pytest.approx(1 / 3 + 1 / 2)

    risk = absolute_risk_at_horizon(np.array([0.5, 2.0]), 0.5)
    np.testing.assert_allclose(risk, 1 - np.exp(-0.5 * np.array([0.5, 2.0])))
    assert ((risk >= 0) & (risk <= 1)).all()


def test_model_predictions_are_deterministic_and_serializable(
    cohort: pd.DataFrame, fitted_model, tmp_path
) -> None:
    features = survival_feature_frame(cohort)
    first = fitted_model.predict_hazard_ratio(features)
    second = fitted_model.predict_hazard_ratio(features)

    assert np.isfinite(first).all() and (first > 0).all()
    np.testing.assert_allclose(first, second)

    path = tmp_path / "survival_cox.json"
    fitted_model.estimator.save_model(str(path))
    reloaded = XGBRegressor()
    reloaded.load_model(str(path))
    np.testing.assert_allclose(reloaded.predict(features), first)


def test_prediction_rejects_feature_contract_mismatch(cohort: pd.DataFrame, fitted_model) -> None:
    features = survival_feature_frame(cohort)
    with pytest.raises(ValueError, match="feature contract"):
        fitted_model.predict_hazard_ratio(features[list(reversed(features.columns))])


def test_cross_validation_is_complete_and_learns_signal(survival_cv, comparison) -> None:
    assert len(survival_cv.oof_risk_5y) == 418
    assert np.isfinite(survival_cv.oof_risk_5y).all()
    assert ((survival_cv.oof_risk_5y >= 0) & (survival_cv.oof_risk_5y <= 1)).all()
    assert len(survival_cv.fold_c_index) == 5
    assert np.isfinite(survival_cv.fold_c_index).all()

    survival = comparison["survival"]
    baseline = comparison["baseline"]
    assert survival["c_index"]["point"] > 0.65
    assert survival["five_year"]["auc"]["point"] > 0.65
    assert survival["five_year"]["n"] == 329
    assert baseline["five_year"]["n"] == 329
    assert np.isfinite(comparison["comparison"]["delta_c_index"])
    assert isinstance(comparison["comparison"]["promote_to_serving"], bool)
    assert comparison["cv"]["horizon_days"] == HORIZON_DAYS
