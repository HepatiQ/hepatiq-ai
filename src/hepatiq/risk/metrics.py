"""Discrimination metrics for time-to-event and binary risk scores."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from sklearn.metrics import roc_auc_score


def harrell_c_index(
    time: np.ndarray,
    event: np.ndarray,
    risk: np.ndarray,
) -> float:
    """Harrell's concordance index for right-censored data.

    Pairs are comparable when the earlier subject had an event. A pair is
    concordant when the subject with the shorter survival also has the higher
    risk. Tied risks count as half a concordance; tied event times are not
    ordered and are skipped.
    """
    time = np.asarray(time, dtype=float)
    event = np.asarray(event).astype(bool)
    risk = np.asarray(risk, dtype=float)

    valid = np.isfinite(time) & np.isfinite(risk) & (time >= 0)
    time, event, risk = time[valid], event[valid], risk[valid]

    concordant = discordant = tied = comparable = 0
    for index in np.flatnonzero(event):
        later = time > time[index]
        if not later.any():
            continue
        comparable += int(later.sum())
        earlier_risk = risk[index]
        concordant += int((risk[later] < earlier_risk).sum())
        discordant += int((risk[later] > earlier_risk).sum())
        tied += int((risk[later] == earlier_risk).sum())

    if comparable == 0:
        return float("nan")
    return (concordant + 0.5 * tied) / comparable


def binary_auc(labels: np.ndarray, scores: np.ndarray) -> float:
    """ROC-AUC over rows with a known binary label."""
    labels = np.asarray(labels, dtype=float)
    scores = np.asarray(scores, dtype=float)
    known = np.isfinite(labels) & np.isfinite(scores)
    if len(np.unique(labels[known])) < 2:
        return float("nan")
    return float(roc_auc_score(labels[known], scores[known]))


def bootstrap_ci(
    metric: Callable[[np.ndarray], float],
    n_rows: int,
    n_boot: int = 1000,
    seed: int = 20261030,
) -> tuple[float, float]:
    """Percentile bootstrap CI; ``metric`` receives resampled row indices."""
    rng = np.random.default_rng(seed)
    values: list[float] = []
    for _ in range(n_boot):
        indices = rng.integers(0, n_rows, n_rows)
        value = metric(indices)
        if np.isfinite(value):
            values.append(value)
    if len(values) < 2:
        return (float("nan"), float("nan"))
    low, high = np.percentile(values, [2.5, 97.5])
    return float(low), float(high)
