"""Metric definitions used by the audit."""

import numpy as np
import pytest

from hepatiq.research.metrics import (
    auc_score,
    bootstrap_ci,
    brier_score,
    calibration_in_the_large,
    calibration_slope_intercept,
    classification_metrics,
    decision_curve,
    expected_calibration_error,
    integrated_calibration_index,
    paired_bootstrap_difference,
    reliability_curve,
)

Y = np.array([0, 0, 0, 0, 1, 1, 1, 1], dtype=float)
P = np.array([0.05, 0.15, 0.35, 0.45, 0.55, 0.65, 0.85, 0.95], dtype=float)


def test_auc_and_brier_are_finite_and_ordered():
    assert auc_score(Y, P) == pytest.approx(1.0)
    assert brier_score(Y, P) == pytest.approx(np.mean((P - Y) ** 2))


def test_auc_requires_two_classes():
    with pytest.raises(ValueError):
        auc_score(np.zeros(5), np.linspace(0, 1, 5))


def test_probability_domain_is_enforced():
    with pytest.raises(ValueError):
        brier_score([0, 1], [0.1, 1.1])
    with pytest.raises(ValueError):
        brier_score([0, 2], [0.1, 0.9])


def test_calibration_curve_and_errors():
    curve = reliability_curve(Y, P, n_bins=4)
    assert curve["counts"].sum() == len(Y)
    assert np.all((curve["prob_pred"] >= 0) & (curve["prob_pred"] <= 1))
    assert np.all((curve["prob_true"] >= 0) & (curve["prob_true"] <= 1))
    assert expected_calibration_error(Y, P, n_bins=4) >= 0
    assert np.isfinite(integrated_calibration_index(Y, P))


def test_calibration_slope_intercept_and_large():
    slope_intercept = calibration_slope_intercept(Y, P)
    assert len(slope_intercept) == 2
    assert all(np.isfinite(value) for value in slope_intercept)
    assert np.isfinite(calibration_in_the_large(Y, P))


def test_classification_metrics_at_threshold():
    metrics = classification_metrics([0, 0, 1, 1], [0.1, 0.6, 0.4, 0.9], 0.5)
    assert (metrics["tp"], metrics["fp"], metrics["tn"], metrics["fn"]) == (1, 1, 1, 1)
    assert metrics["sensitivity"] == pytest.approx(0.5)
    assert metrics["specificity"] == pytest.approx(0.5)
    assert metrics["f1"] == pytest.approx(0.5)


def test_decision_curve_has_expected_shapes():
    curve = decision_curve(Y, P, thresholds=(0.1, 0.5))
    assert curve["model"].shape == (2,)
    assert curve["treat_all"].shape == (2,)
    with pytest.raises(ValueError):
        decision_curve(Y, P, thresholds=(0.0,))


def test_bootstrap_ci_and_paired_difference():
    y = np.array([0] * 30 + [1] * 30)
    p = np.array([0.1] * 30 + [0.9] * 30)
    interval = bootstrap_ci(y, p, auc_score, n_boot=50, seed=7)
    assert interval["point"] == pytest.approx(1.0)
    assert interval["lower"] == pytest.approx(1.0)
    assert interval["upper"] == pytest.approx(1.0)

    diff = paired_bootstrap_difference(y, p, p, auc_score, n_boot=50, seed=7)
    assert diff["point"] == pytest.approx(0.0)
    assert diff["lower"] == pytest.approx(0.0)
    assert diff["upper"] == pytest.approx(0.0)
