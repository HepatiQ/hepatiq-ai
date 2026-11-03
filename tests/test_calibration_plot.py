"""Calibration plot tests: genuine OOF reliability curve, no hardcoded points."""

import matplotlib

matplotlib.use("Agg")

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from hepatiq.validation import calibration_plot


def test_reliability_curve_uses_quantile_bins():
    y_true = np.array([0, 0, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.8, 0.9])

    prob_pred, prob_true, counts = calibration_plot.reliability_curve(y_true, y_prob, n_bins=2)

    np.testing.assert_allclose(prob_pred, [0.15, 0.85])
    np.testing.assert_allclose(prob_true, [0.0, 1.0])
    np.testing.assert_array_equal(counts, [2, 2])
    assert counts.sum() == len(y_true)


@pytest.mark.parametrize(
    ("y_true", "y_prob", "n_bins", "message"),
    [
        (np.array([0, 1]), np.array([0.2]), 2, "equal lengths"),
        (np.array([]), np.array([]), 2, "must not be empty"),
        (np.array([0, 1]), np.array([0.2, 1.1]), 2, "in \\[0, 1\\]"),
        (np.array([0, 1]), np.array([0.2, np.nan]), 2, "finite"),
        (np.array([0, 1]), np.array([0.2, 0.8]), 1, "at least 2"),
        (np.array([0, 1]), np.array([0.2, 0.8]), 3, "must not exceed"),
        (np.array([0, 2]), np.array([0.2, 0.8]), 2, "only 0 and 1"),
        (np.array([1, 1]), np.array([0.2, 0.8]), 2, "both classes"),
    ],
)
def test_reliability_curve_rejects_invalid_input(y_true, y_prob, n_bins, message):
    with pytest.raises(ValueError, match=message):
        calibration_plot.reliability_curve(y_true, y_prob, n_bins=n_bins)


def test_main_source_has_no_hardcoded_curve_arrays():
    source = Path(calibration_plot.__file__).read_text(encoding="utf-8")
    assert "prob_true = np.array" not in source
    assert "prob_pred = np.array" not in source


def test_main_uses_oof_predictions_and_writes_plot(tmp_path, monkeypatch):
    target = pd.Series([0] * 10 + [1] * 10)
    features = pd.DataFrame({"x": list(range(20))})
    calls = {}

    def fake_oof(features_arg, target_arg):
        calls["target_n"] = len(target_arg)
        probabilities = np.linspace(0.01, 0.99, len(target_arg))
        return probabilities, np.full(len(target_arg), 0.5)

    monkeypatch.setattr(calibration_plot.pd, "read_csv", lambda _path: pd.DataFrame({"x": features["x"]}))
    monkeypatch.setattr(
        calibration_plot,
        "build_feature_frame",
        lambda _df: (features, None, target),
    )
    monkeypatch.setattr(calibration_plot, "out_of_fold_predictions", fake_oof)
    output = tmp_path / "calibration_plot.png"
    monkeypatch.setattr(calibration_plot, "CALIBRATION_PLOT_PATH", output)

    calibration_plot.main()

    assert calls["target_n"] == 20
    assert output.exists()
    assert output.stat().st_size > 0


def test_main_rejects_empty_oof_predictions(monkeypatch):
    target = pd.Series([0, 0, 1, 1])
    features = pd.DataFrame({"x": [1, 2, 3, 4]})

    monkeypatch.setattr(calibration_plot.pd, "read_csv", lambda _path: pd.DataFrame({"x": features["x"]}))
    monkeypatch.setattr(
        calibration_plot,
        "build_feature_frame",
        lambda _df: (features, None, target),
    )
    monkeypatch.setattr(
        calibration_plot,
        "out_of_fold_predictions",
        lambda _features, _target: (np.array([]), np.array([])),
    )

    with pytest.raises(ValueError, match="empty"):
        calibration_plot.main()
