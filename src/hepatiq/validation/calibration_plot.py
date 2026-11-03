#!/usr/bin/env python
"""Reliability diagram from genuine out-of-fold predictions."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from hepatiq.ml.impute_pipeline import build_feature_frame
from hepatiq.paths import CALIBRATION_PLOT_PATH, PROCESSED_DATA
from hepatiq.validation.run_validation import N_FOLDS, SEED, out_of_fold_predictions


def reliability_curve(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (prob_pred, prob_true, counts) using quantile bins.

    Empty bins are dropped from the returned curve but remain visible in the
    input validation; callers can compare the returned count sum to n.
    """
    labels = np.asarray(y_true, dtype=float).ravel()
    probabilities = np.asarray(y_prob, dtype=float).ravel()

    if labels.size != probabilities.size:
        raise ValueError("y_true and y_prob must have equal lengths")
    if labels.size == 0:
        raise ValueError("y_true and y_prob must not be empty")
    if n_bins < 2:
        raise ValueError("n_bins must be at least 2")
    if n_bins > labels.size:
        raise ValueError("n_bins must not exceed the number of observations")
    if not np.isfinite(probabilities).all():
        raise ValueError("y_prob must contain only finite values")
    if np.any((probabilities < 0.0) | (probabilities > 1.0)):
        raise ValueError("y_prob must be in [0, 1]")
    if not np.isin(labels, (0.0, 1.0)).all():
        raise ValueError("y_true must contain only 0 and 1")
    if np.unique(labels).size < 2:
        raise ValueError("y_true must contain both classes")

    edges = np.percentile(probabilities, np.linspace(0.0, 100.0, n_bins + 1))
    bin_ids = np.searchsorted(edges[1:-1], probabilities)
    bin_total = np.bincount(bin_ids, minlength=n_bins)
    bin_probability = np.bincount(bin_ids, weights=probabilities, minlength=n_bins)
    bin_positive = np.bincount(bin_ids, weights=labels, minlength=n_bins)

    nonempty = bin_total > 0
    prob_pred = bin_probability[nonempty] / bin_total[nonempty]
    prob_true = bin_positive[nonempty] / bin_total[nonempty]
    counts = bin_total[nonempty].astype(int)
    return prob_pred, prob_true, counts


def main() -> None:
    df = pd.read_csv(PROCESSED_DATA)
    features, _ids, target = build_feature_frame(df)
    model_oof, _prior_oof = out_of_fold_predictions(features, target)
    model_oof = np.asarray(model_oof, dtype=float)

    if model_oof.size == 0:
        raise ValueError("out_of_fold_predictions returned an empty array")
    if model_oof.size != len(target):
        raise ValueError("out_of_fold_predictions returned the wrong number of predictions")

    y = target.to_numpy()
    prob_pred, prob_true, counts = reliability_curve(y, model_oof)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot([0, 1], [0, 1], "k--", label="Perfect calibration")
    ax.plot(prob_pred, prob_true, "s-", label="Logistic Regression (OOF)", markersize=8)
    for mean_predicted, observed, count in zip(prob_pred, prob_true, counts, strict=True):
        ax.annotate(
            f"n={count}",
            (mean_predicted, observed),
            textcoords="offset points",
            xytext=(6, 6),
            fontsize=8,
        )
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Fraction of positives")
    ax.set_title("Reliability Diagram - HepatiQ OOF Predictions")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)
    fig.savefig(CALIBRATION_PLOT_PATH, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(
        f"OOF reliability diagram: n={len(y)} events={int(y.sum())} "
        f"folds={N_FOLDS} seed={SEED}"
    )
    print(f"prob_pred={prob_pred.round(6).tolist()}")
    print(f"prob_true={prob_true.round(6).tolist()}")
    print(f"counts={counts.tolist()}")
    print(f"Saved {CALIBRATION_PLOT_PATH}")


if __name__ == "__main__":
    main()
