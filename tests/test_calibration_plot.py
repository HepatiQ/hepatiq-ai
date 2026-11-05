"""Calibration plot tests: genuine OOF reliability curve, no hardcoded points."""

import matplotlib

matplotlib.use("Agg")

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from matplotlib.figure import Figure

from hepatiq.validation import calibration_plot


def _patch_main(monkeypatch, target, features, oof, prior, output):
    monkeypatch.setattr(calibration_plot, "load_data", lambda: features.copy())
    monkeypatch.setattr(
        calibration_plot,
        "build_feature_frame",
        lambda _df: (features, None, target),
    )
    monkeypatch.setattr(
        calibration_plot,
        "out_of_fold_predictions",
        lambda _features, _target: (oof, prior),
    )
    monkeypatch.setattr(calibration_plot, "CALIBRATION_PLOT_PATH", output)


def test_reliability_curve_uses_quantile_bins():
    y_true = np.array([0, 0, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.8, 0.9])

    prob_pred, prob_true, counts = calibration_plot.reliability_curve(y_true, y_prob, n_bins=2)

    np.testing.assert_allclose(prob_pred, [0.15, 0.85])
    np.testing.assert_allclose(prob_true, [0.0, 1.0])
    np.testing.assert_array_equal(counts, [2, 2])
    assert counts.sum() == len(y_true)


def test_reliability_curve_assigns_edge_tie_to_higher_bin():
    y_true = np.array([0, 1, 0, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.5, 0.6, 0.9])

    prob_pred, prob_true, counts = calibration_plot.reliability_curve(y_true, y_prob, n_bins=2)

    np.testing.assert_allclose(prob_pred, [0.15, 2.0 / 3.0])
    np.testing.assert_allclose(prob_true, [0.5, 2.0 / 3.0])
    np.testing.assert_array_equal(counts, [2, 3])


def test_reliability_curve_collapses_duplicate_quantile_edges():
    y_true = np.array([0, 0, 1, 1, 0, 1])
    y_prob = np.array([0.1, 0.1, 0.9, 0.9, 0.1, 0.9])

    prob_pred, prob_true, counts = calibration_plot.reliability_curve(y_true, y_prob, n_bins=4)

    np.testing.assert_allclose(prob_pred, [0.1, 0.9])
    np.testing.assert_allclose(prob_true, [0.0, 1.0])
    np.testing.assert_array_equal(counts, [3, 3])
    assert counts.sum() == len(y_true)


def test_reliability_curve_drops_interior_empty_bin_and_preserves_total_count():
    y_true = np.array([0, 1, 0, 1])
    y_prob = np.array([0.0, 0.5, 0.5, 1.0])

    prob_pred, prob_true, counts = calibration_plot.reliability_curve(y_true, y_prob, n_bins=4)

    np.testing.assert_allclose(prob_pred, [0.0, 0.5, 1.0])
    np.testing.assert_allclose(prob_true, [0.0, 0.5, 1.0])
    np.testing.assert_array_equal(counts, [1, 2, 1])
    assert counts.sum() == len(y_true)


def test_reliability_curve_handles_boundary_probabilities():
    prob_pred, prob_true, counts = calibration_plot.reliability_curve(
        np.array([0, 1]),
        np.array([0.0, 1.0]),
        n_bins=2,
    )

    np.testing.assert_allclose(prob_pred, [0.0, 1.0])
    np.testing.assert_allclose(prob_true, [0.0, 1.0])
    np.testing.assert_array_equal(counts, [1, 1])


def test_reliability_curve_asymmetric_three_bins():
    prob_pred, prob_true, counts = calibration_plot.reliability_curve(
        np.array([0, 0, 1, 1, 0, 1]),
        np.array([0.1, 0.2, 0.3, 0.6, 0.8, 0.9]),
        n_bins=3,
    )

    np.testing.assert_allclose(prob_pred, [0.15, 0.45, 0.85])
    np.testing.assert_allclose(prob_true, [0.0, 1.0, 0.5])
    np.testing.assert_array_equal(counts, [2, 2, 2])


def test_reliability_curve_handles_identical_probabilities():
    prob_pred, prob_true, counts = calibration_plot.reliability_curve(
        np.array([0, 1]),
        np.array([0.5, 0.5]),
        n_bins=2,
    )

    np.testing.assert_allclose(prob_pred, [0.5])
    np.testing.assert_allclose(prob_true, [0.5])
    np.testing.assert_array_equal(counts, [2])


def test_reliability_curve_is_deterministic():
    y_true = np.array([0, 0, 1, 1, 0, 1])
    y_prob = np.array([0.1, 0.2, 0.8, 0.9, 0.3, 0.7])

    first = calibration_plot.reliability_curve(y_true, y_prob, n_bins=3)
    second = calibration_plot.reliability_curve(y_true, y_prob, n_bins=3)

    for left, right in zip(first, second, strict=True):
        np.testing.assert_array_equal(left, right)


@pytest.mark.parametrize(
    ("y_true", "y_prob", "n_bins", "message"),
    [
        (np.array([0, 1]), np.array([0.2]), 2, "equal lengths"),
        (np.array([]), np.array([]), 2, "must not be empty"),
        (np.array([0, 1]), np.array([-0.1, 0.8]), 2, "in \\[0, 1\\]"),
        (np.array([0, 1]), np.array([0.2, 1.1]), 2, "in \\[0, 1\\]"),
        (np.array([0, 1]), np.array([0.2, np.inf]), 2, "finite"),
        (np.array([0, 1]), np.array([0.2, np.nan]), 2, "finite"),
        (np.array([0, 1]), np.array([0.2, 0.8]), 2.5, "integer"),
        (np.array([0, 1]), np.array([0.2, 0.8]), 1, "at least 2"),
        (np.array([0, 1]), np.array([0.2, 0.8]), 3, "must not exceed"),
        (np.array([0, np.nan]), np.array([0.2, 0.8]), 2, "only 0 and 1"),
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
    oof = np.linspace(0.01, 0.99, len(target))
    calls = {}

    def fake_oof(features_arg, target_arg):
        calls["target_n"] = len(target_arg)
        return oof, np.full(len(target_arg), 0.5)

    _patch_main(
        monkeypatch,
        target,
        features,
        oof,
        np.full(len(target), 0.5),
        tmp_path / "calibration_plot.png",
    )
    monkeypatch.setattr(calibration_plot, "out_of_fold_predictions", fake_oof)

    calibration_plot.main()

    assert calls["target_n"] == 20
    output = tmp_path / "calibration_plot.png"
    assert output.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_main_rejects_empty_oof_predictions(tmp_path, monkeypatch):
    target = pd.Series([0, 0, 1, 1])
    features = pd.DataFrame({"x": [1, 2, 3, 4]})
    output = tmp_path / "unused.png"

    _patch_main(
        monkeypatch,
        target,
        features,
        np.array([]),
        np.array([]),
        output,
    )

    with pytest.raises(ValueError, match="empty"):
        calibration_plot.main()


def test_main_rejects_wrong_length_oof_predictions(tmp_path, monkeypatch):
    target = pd.Series([0, 0, 1, 1, 0, 1])
    features = pd.DataFrame({"x": range(len(target))})
    output = tmp_path / "unused.png"

    _patch_main(
        monkeypatch,
        target,
        features,
        np.linspace(0.1, 0.9, len(target) - 1),
        np.full(len(target) - 1, 0.5),
        output,
    )

    with pytest.raises(ValueError, match="wrong number of predictions"):
        calibration_plot.main()


def test_main_passes_target_and_model_oof_to_reliability_curve(tmp_path, monkeypatch):
    target = pd.Series([0] * 10 + [1] * 10)
    features = pd.DataFrame({"x": range(20)})
    oof = np.linspace(0.01, 0.99, len(target))
    prior = np.zeros(len(target))
    captured = {}

    def spy(y_true, y_prob, n_bins=10):
        captured["y_true"] = np.asarray(y_true).copy()
        captured["y_prob"] = np.asarray(y_prob).copy()
        return np.array([0.2, 0.8]), np.array([0.1, 0.9]), np.array([10, 10])

    _patch_main(
        monkeypatch,
        target,
        features,
        oof,
        prior,
        tmp_path / "calibration_plot.png",
    )
    monkeypatch.setattr(calibration_plot, "reliability_curve", spy)

    calibration_plot.main()

    np.testing.assert_array_equal(captured["y_true"], target.to_numpy())
    np.testing.assert_allclose(captured["y_prob"], oof)
    assert not np.array_equal(captured["y_prob"], prior)


def test_main_plots_curve_from_oof_not_hardcoded(tmp_path, monkeypatch):
    target = pd.Series([0] * 10 + [1] * 10)
    features = pd.DataFrame({"x": range(20)})
    oof = np.linspace(0.01, 0.99, len(target))
    output = tmp_path / "calibration_plot.png"
    captured = {}

    _patch_main(
        monkeypatch,
        target,
        features,
        oof,
        np.full(len(target), 0.5),
        output,
    )

    real_savefig = Figure.savefig

    def spy(fig, *args, **kwargs):
        line = fig.axes[0].lines[1]
        captured["x"] = np.asarray(line.get_xdata()).copy()
        captured["y"] = np.asarray(line.get_ydata()).copy()
        return real_savefig(fig, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", spy)

    calibration_plot.main()

    expected_x, expected_y, _ = calibration_plot.reliability_curve(target.to_numpy(), oof)
    np.testing.assert_allclose(captured["x"], expected_x)
    np.testing.assert_allclose(captured["y"], expected_y)
    assert output.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
