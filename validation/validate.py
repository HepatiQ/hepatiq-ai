"""Validation helpers (placeholders)

This module contains small utilities to be expanded by the validation lead.
"""

import numpy as np
from typing import Callable, Tuple


def bootstrap_ci(preds: np.ndarray, labels: np.ndarray, stat_func: Callable[[np.ndarray, np.ndarray], float], n_boot: int = 1000, seed: int = 0) -> Tuple[float, float]:
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
    """Placeholder for MELD benchmarking: compute and return comparison metrics.

    Real implementation should compute Brier score, AUC, calibration curves, etc.
    """
    return {"brier_model": None, "brier_meld": None}
