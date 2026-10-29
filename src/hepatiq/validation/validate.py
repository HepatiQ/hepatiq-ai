"""Validation helpers

This module contains small utilities for the clinical-validation workflow.
"""

from typing import Callable, Tuple

import numpy as np
from sklearn.metrics import brier_score_loss, roc_auc_score


def bootstrap_ci(
    preds: np.ndarray,
    labels: np.ndarray,
    stat_func: Callable[[np.ndarray, np.ndarray], float],
    n_boot: int = 1000,
    seed: int = 0,
) -> Tuple[float, float]:
    """Compute a bootstrap confidence interval for a statistic.

    preds and labels should be 1-D arrays of the same length. stat_func(labels, preds) -> float.
    """
    rng = np.random.RandomState(seed)
    stats = []
    n = len(preds)
    for _ in range(n_boot):
        idx = rng.randint(0, n, n)
        stats.append(stat_func(labels[idx], preds[idx]))
    lower = np.percentile(stats, 2.5)
    upper = np.percentile(stats, 97.5)
    return lower, upper


def compare_to_meld(preds: np.ndarray, labels: np.ndarray, meld_scores: np.ndarray) -> dict:
    """Benchmark model predictions against MELD scores.

    AUC is rank-based and scale-invariant, so it is computed on the raw
    scores for both. Brier score requires probabilities; MELD is a risk
    score (not a probability), so it is min-max scaled to [0, 1] first.
    That scaling is a crude calibration and brier_meld should be treated
    as indicative only. Metrics that are undefined (AUC when only one
    class is present in labels) are None.
    """
    preds = np.asarray(preds, dtype=float)
    labels = np.asarray(labels, dtype=float)
    meld_scores = np.asarray(meld_scores, dtype=float)

    empty = {
        "n": int(len(labels)),
        "n_events": 0,
        "brier_model": None,
        "brier_meld": None,
        "auc_model": None,
        "auc_meld": None,
    }
    if len(labels) == 0:
        return empty

    out = {
        "n": int(len(labels)),
        "n_events": int((labels == 1).sum()),
        "brier_model": float(brier_score_loss(labels, preds)),
        "brier_meld": None,
        "auc_model": None,
        "auc_meld": None,
    }

    lo, hi = float(meld_scores.min()), float(meld_scores.max())
    meld_prob = (meld_scores - lo) / (hi - lo) if hi > lo else np.full_like(meld_scores, 0.5)
    out["brier_meld"] = float(brier_score_loss(labels, meld_prob))

    if len(np.unique(labels)) > 1:
        out["auc_model"] = float(roc_auc_score(labels, preds))
        out["auc_meld"] = float(roc_auc_score(labels, meld_scores))

    return out
