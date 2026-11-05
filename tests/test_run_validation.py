"""Tests for validation/run_validation.py: scoring, report formatting, committed artifact."""

import numpy as np
import pandas as pd
import pytest

from hepatiq.paths import VALIDATION_REPORT_PATH
from hepatiq.validation import run_validation
from hepatiq.validation.run_validation import build_report, score

COHORT = {"n": 200, "events": 80, "nonevents": 120, "features": 17}


def _synthetic_predictions():
    rng = np.random.RandomState(0)
    labels = np.array([0] * 100 + [1] * 100)
    rng.shuffle(labels)
    preds = np.clip(rng.normal(0.5, 0.2, 200) + 0.15 * (labels - 0.5), 0.0, 1.0)
    return preds, labels


def test_score_returns_all_metrics_with_point_inside_ci():
    preds, labels = _synthetic_predictions()
    results = score(preds, labels)
    assert set(results) == {"ROC-AUC", "Brier score (lower=better)", "Precision", "Recall", "F1"}
    for name, r in results.items():
        assert r["lower"] <= r["point"] <= r["upper"], name


def test_score_is_deterministic():
    preds, labels = _synthetic_predictions()
    assert score(preds, labels) == score(preds, labels)


def test_build_report_contains_headline_numbers():
    preds, labels = _synthetic_predictions()
    model_scores = score(preds, labels)
    prior_scores = score(np.full(len(labels), labels.mean()), labels)
    report = build_report(model_scores, prior_scores, COHORT)

    assert "# HepatiQ Validation Report" in report
    assert "Patients: **200** (80 severe events / 120 event-free)" in report
    assert "| Metric | HepatiQ model | Class-prior baseline |" in report
    assert "5-fold stratified CV (seed 42)" in report
    assert "lacks creatinine and" in report
    assert "MELD is not computable here" in report
    for name in model_scores:
        assert f"| {name} |" in report


def test_committed_report_exists_and_has_current_headline():
    report = VALIDATION_REPORT_PATH.read_text(encoding="utf-8")
    assert "## Results (OOF, n=329)" in report
    assert "0.8828" in report  # regenerate with: python validation/run_validation.py

class _RecordingPipeline:
    def __init__(self, feature_names=None):
        self.feature_names_in_ = np.array(feature_names) if feature_names else None
        self.train_index = []
        self.predicted_index = []

    def fit(self, features, target):
        self.train_index = list(features.index)
        return self

    def predict_proba(self, features):
        self.predicted_index = list(features.index)
        probabilities = (features["x"].to_numpy() + 1) / 100.0
        return np.column_stack([1 - probabilities, probabilities])


def _oof_fixture(n=30):
    index = pd.Index([f"p{i}" for i in range(n)])
    features = pd.DataFrame({"x": np.arange(n)}, index=index)
    target = pd.Series([1 if i < n // 3 else 0 for i in range(n)], index=index)
    return features, target


def test_out_of_fold_predictions_are_aligned_and_leakage_free(monkeypatch):
    features, target = _oof_fixture()
    pipes = []

    def fake_load(_path):
        pipe = _RecordingPipeline()
        pipes.append(pipe)
        return pipe

    monkeypatch.setattr(run_validation.joblib, "load", fake_load)

    model_oof, prior_oof = run_validation.out_of_fold_predictions(features, target)

    assert model_oof.shape == (len(target),)
    assert prior_oof.shape == (len(target),)
    predicted = [index for pipe in pipes for index in pipe.predicted_index]
    assert sorted(predicted) == sorted(features.index)
    assert len(predicted) == len(target)

    expected = (features["x"].to_numpy() + 1) / 100.0
    for pipe in pipes:
        positions = features.index.get_indexer(pipe.predicted_index)
        assert set(pipe.train_index).isdisjoint(pipe.predicted_index)
        np.testing.assert_allclose(model_oof[positions], expected[positions])
        np.testing.assert_allclose(
            prior_oof[positions],
            np.full(len(positions), target.loc[pipe.train_index].mean()),
        )


def test_out_of_fold_predictions_are_deterministic(monkeypatch):
    features, target = _oof_fixture()

    def run_once():
        pipes = []

        def fake_load(_path):
            pipe = _RecordingPipeline()
            pipes.append(pipe)
            return pipe

        monkeypatch.setattr(run_validation.joblib, "load", fake_load)
        model_oof, prior_oof = run_validation.out_of_fold_predictions(features, target)
        return model_oof, prior_oof, [pipe.train_index for pipe in pipes]

    first = run_once()
    second = run_once()

    np.testing.assert_array_equal(first[0], second[0])
    np.testing.assert_array_equal(first[1], second[1])
    assert first[2] == second[2]


def test_out_of_fold_predictions_reject_misaligned_inputs():
    features, target = _oof_fixture()

    with pytest.raises(ValueError, match="equal lengths"):
        run_validation.out_of_fold_predictions(features.iloc[:-1], target)

    shifted = target.copy()
    shifted.index = [f"q{i}" for i in range(len(target))]
    with pytest.raises(ValueError, match="same index"):
        run_validation.out_of_fold_predictions(features, shifted)

    nonbinary = target.copy()
    nonbinary.iloc[0] = 2
    with pytest.raises(ValueError, match="only 0 and 1"):
        run_validation.out_of_fold_predictions(features, nonbinary)


def test_out_of_fold_predictions_accept_matching_feature_columns(monkeypatch):
    features, target = _oof_fixture(n=20)
    monkeypatch.setattr(
        run_validation.joblib,
        "load",
        lambda _path: _RecordingPipeline(feature_names=["x"]),
    )

    model_oof, prior_oof = run_validation.out_of_fold_predictions(features, target)

    assert model_oof.shape == (len(target),)
    assert prior_oof.shape == (len(target),)


def test_out_of_fold_predictions_reject_unexpected_feature_columns(monkeypatch):
    features, target = _oof_fixture(n=20)
    features = features.assign(extra=1.0)
    monkeypatch.setattr(
        run_validation.joblib,
        "load",
        lambda _path: _RecordingPipeline(feature_names=["x"]),
    )

    with pytest.raises(ValueError, match="feature columns do not match"):
        run_validation.out_of_fold_predictions(features, target)


def test_out_of_fold_predictions_reject_reordered_feature_columns(monkeypatch):
    features, target = _oof_fixture(n=20)
    features = features.assign(y=0.0)[["y", "x"]]
    monkeypatch.setattr(
        run_validation.joblib,
        "load",
        lambda _path: _RecordingPipeline(feature_names=["x", "y"]),
    )

    with pytest.raises(ValueError, match="feature columns do not match"):
        run_validation.out_of_fold_predictions(features, target)
