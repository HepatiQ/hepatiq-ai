"""Tests for validation/run_validation.py: scoring, report formatting, committed artifact."""

import numpy as np

from validation.run_validation import build_report, score

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
    from pathlib import Path

    report = (Path(__file__).resolve().parents[1] / "validation" / "report.md").read_text(encoding="utf-8")
    assert "## Results (OOF, n=329)" in report
    assert "0.8828" in report  # regenerate with: python validation/run_validation.py
