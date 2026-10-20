"""validation/validate.py unit tests: bootstrap_ci and compare_to_meld."""

import numpy as np

from validation.validate import bootstrap_ci, compare_to_meld


def test_bootstrap_ci_brackets_the_statistic():
    preds = np.arange(1, 41, dtype=float)
    labels = np.zeros(40)
    lower, upper = bootstrap_ci(preds, labels, lambda y, p: float(np.mean(p)), n_boot=500, seed=0)
    assert lower < preds.mean() < upper


def test_bootstrap_ci_is_deterministic_for_a_fixed_seed():
    preds = np.random.RandomState(1).rand(50)
    labels = np.random.RandomState(2).randint(0, 2, 50)
    def stat(y, p):
        return float(np.mean(y))

    a = bootstrap_ci(preds, labels, stat, n_boot=200, seed=7)
    b = bootstrap_ci(preds, labels, stat, n_boot=200, seed=7)
    assert a == b


def test_compare_to_meld_happy_path():
    preds = np.array([0.1, 0.4, 0.35, 0.8])
    labels = np.array([0, 0, 1, 1])
    meld = np.array([8.0, 12.0, 15.0, 22.0])
    out = compare_to_meld(preds, labels, meld)
    assert out["n"] == 4
    assert out["n_events"] == 2
    assert out["auc_model"] == 0.75
    assert out["auc_meld"] == 1.0
    assert 0.0 <= out["brier_model"] <= 1.0
    assert 0.0 <= out["brier_meld"] <= 1.0


def test_compare_to_meld_single_class_returns_none_aucs():
    out = compare_to_meld(np.array([0.2, 0.6]), np.array([1, 1]), np.array([10.0, 20.0]))
    assert out["auc_model"] is None
    assert out["auc_meld"] is None
    assert out["brier_model"] is not None


def test_compare_to_meld_empty_input():
    out = compare_to_meld(np.array([]), np.array([]), np.array([]))
    assert out["n"] == 0
    assert all(out[k] is None for k in ("brier_model", "brier_meld", "auc_model", "auc_meld"))
