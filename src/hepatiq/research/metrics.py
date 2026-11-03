"""Calibration and discrimination metrics used by the frozen audit."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
from scipy.optimize import minimize_scalar
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, confusion_matrix, roc_auc_score

from hepatiq.research.config import N_BOOTSTRAP, N_CALIBRATION_BINS

EPS = 1e-6


def _arrays(y_true, y_prob) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(y_true, dtype=float).reshape(-1)
    p = np.asarray(y_prob, dtype=float).reshape(-1)
    if len(y) != len(p):
        raise ValueError("y_true and y_prob must have the same length")
    if len(y) == 0:
        raise ValueError("metrics require at least one observation")
    if not np.isfinite(y).all() or not np.isfinite(p).all():
        raise ValueError("y_true and y_prob must be finite")
    if not np.isin(y, [0.0, 1.0]).all():
        raise ValueError("y_true must contain only 0 and 1")
    if (p < 0).any() or (p > 1).any():
        raise ValueError("y_prob must be in [0, 1]")
    return y, p


def _require_two_classes(y: np.ndarray) -> None:
    if len(np.unique(y)) < 2:
        raise ValueError("metric requires both outcome classes")


def logit(prob: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(prob, dtype=float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


def auc_score(y_true, y_prob) -> float:
    y, p = _arrays(y_true, y_prob)
    _require_two_classes(y)
    return float(roc_auc_score(y, p))


def brier_score(y_true, y_prob) -> float:
    y, p = _arrays(y_true, y_prob)
    return float(brier_score_loss(y, p))


def calibration_slope_intercept(y_true, y_prob) -> tuple[float, float]:
    """Return (slope, intercept) for logit(y) = intercept + slope * logit(p)."""
    y, p = _arrays(y_true, y_prob)
    _require_two_classes(y)
    if np.unique(p).size < 2:
        return float("nan"), float("nan")
    model = LogisticRegression(C=np.inf, l1_ratio=0, solver="lbfgs", max_iter=1000)
    model.fit(logit(p).reshape(-1, 1), y)
    return float(model.coef_[0, 0]), float(model.intercept_[0])


def calibration_in_the_large(y_true, y_prob) -> float:
    """Intercept from a logistic model with the calibration slope fixed at 1."""
    y, p = _arrays(y_true, y_prob)
    lp = logit(p)

    def nll(intercept: float) -> float:
        z = intercept + lp
        return float(np.mean(np.logaddexp(0, z) - y * z))

    result = minimize_scalar(nll, bounds=(-10.0, 10.0), method="bounded")
    return float(result.x)


def reliability_curve(
    y_true,
    y_prob,
    n_bins: int = N_CALIBRATION_BINS,
) -> dict[str, np.ndarray]:
    """Quantile-binned reliability curve with counts for every returned bin."""
    y, p = _arrays(y_true, y_prob)
    if n_bins < 1:
        raise ValueError("n_bins must be positive")

    edges = np.unique(np.quantile(p, np.linspace(0.0, 1.0, n_bins + 1)))
    if edges.size < 2:
        bins = np.zeros(len(p), dtype=int)
    else:
        bins = np.searchsorted(edges[1:-1], p, side="right")

    prob_pred: list[float] = []
    prob_true: list[float] = []
    counts: list[int] = []
    for bin_id in np.unique(bins):
        mask = bins == bin_id
        prob_pred.append(float(p[mask].mean()))
        prob_true.append(float(y[mask].mean()))
        counts.append(int(mask.sum()))
    return {
        "prob_pred": np.asarray(prob_pred, dtype=float),
        "prob_true": np.asarray(prob_true, dtype=float),
        "counts": np.asarray(counts, dtype=int),
    }


def expected_calibration_error(y_true, y_prob, n_bins: int = N_CALIBRATION_BINS) -> float:
    y, p = _arrays(y_true, y_prob)
    curve = reliability_curve(y, p, n_bins=n_bins)
    weights = curve["counts"] / len(y)
    return float(np.sum(weights * np.abs(curve["prob_true"] - curve["prob_pred"])))


def integrated_calibration_index(y_true, y_prob) -> float:
    """Mean absolute difference between observed and isotonic-smoothed risk."""
    y, p = _arrays(y_true, y_prob)
    if len(np.unique(p)) < 2:
        return float("nan")
    iso = IsotonicRegression(out_of_bounds="clip")
    smoothed = iso.fit_transform(p, y)
    return float(np.mean(np.abs(y - smoothed)))


def classification_metrics(y_true, y_prob, threshold: float) -> dict[str, float | int]:
    y, p = _arrays(y_true, y_prob)
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be in [0, 1]")
    pred = (p >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    npv = tn / (tn + fn) if (tn + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "threshold": float(threshold),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "precision": float(precision),
        "recall": float(recall),
        "sensitivity": float(recall),
        "specificity": float(specificity),
        "ppv": float(precision),
        "npv": float(npv),
        "f1": float(f1),
    }


def decision_curve(
    y_true,
    y_prob,
    thresholds: Sequence[float],
) -> dict[str, np.ndarray]:
    y, p = _arrays(y_true, y_prob)
    n = len(y)
    prevalence = float(y.mean())
    model_nb: list[float] = []
    treat_all_nb: list[float] = []
    for threshold in thresholds:
        if not 0 < threshold < 1:
            raise ValueError("decision thresholds must be strictly between 0 and 1")
        pred = p >= threshold
        tp = int(np.sum(pred & (y == 1)))
        fp = int(np.sum(pred & (y == 0)))
        weight = threshold / (1 - threshold)
        model_nb.append(tp / n - fp / n * weight)
        treat_all_nb.append(prevalence - (1 - prevalence) * weight)
    return {
        "thresholds": np.asarray(thresholds, dtype=float),
        "model": np.asarray(model_nb, dtype=float),
        "treat_all": np.asarray(treat_all_nb, dtype=float),
    }


def bootstrap_ci(
    y_true,
    y_prob,
    metric_fn: Callable[[np.ndarray, np.ndarray], float],
    *,
    n_boot: int = N_BOOTSTRAP,
    seed: int = 42,
) -> dict[str, float | int]:
    y, p = _arrays(y_true, y_prob)
    point = float(metric_fn(y, p))
    rng = np.random.RandomState(seed)
    values: list[float] = []
    for _ in range(n_boot):
        idx = rng.randint(0, len(y), len(y))
        try:
            value = float(metric_fn(y[idx], p[idx]))
        except ValueError:
            continue
        if np.isfinite(value):
            values.append(value)

    if not values:
        return {"point": point, "lower": float("nan"), "upper": float("nan"), "n_valid": 0}
    lower, upper = np.percentile(values, [2.5, 97.5])
    return {
        "point": point,
        "lower": float(lower),
        "upper": float(upper),
        "n_valid": len(values),
    }


def paired_bootstrap_difference(
    y_true,
    prob_a,
    prob_b,
    metric_fn: Callable[[np.ndarray, np.ndarray], float],
    *,
    n_boot: int = N_BOOTSTRAP,
    seed: int = 42,
) -> dict[str, float | int]:
    y, a = _arrays(y_true, prob_a)
    _, b = _arrays(y_true, prob_b)
    point = float(metric_fn(y, a) - metric_fn(y, b))
    rng = np.random.RandomState(seed)
    diffs: list[float] = []
    for _ in range(n_boot):
        idx = rng.randint(0, len(y), len(y))
        try:
            diff = float(metric_fn(y[idx], a[idx]) - metric_fn(y[idx], b[idx]))
        except ValueError:
            continue
        if np.isfinite(diff):
            diffs.append(diff)
    if not diffs:
        return {"point": point, "lower": float("nan"), "upper": float("nan"), "p_value": float("nan")}

    lower, upper = np.percentile(diffs, [2.5, 97.5])
    values = np.asarray(diffs)
    p_value = min(1.0, 2.0 * min(float(np.mean(values <= 0)), float(np.mean(values >= 0))))
    return {
        "point": point,
        "lower": float(lower),
        "upper": float(upper),
        "p_value": p_value,
    }


def evaluate_probabilities(
    y_true,
    y_prob,
    *,
    n_boot: int = N_BOOTSTRAP,
    seed: int = 42,
) -> dict[str, object]:
    y, p = _arrays(y_true, y_prob)
    slope, intercept = calibration_slope_intercept(y, p)
    curve = reliability_curve(y, p)
    return {
        "n": int(len(y)),
        "events": int(y.sum()),
        "auc": bootstrap_ci(y, p, auc_score, n_boot=n_boot, seed=seed),
        "brier": bootstrap_ci(y, p, brier_score, n_boot=n_boot, seed=seed),
        "calibration_slope": slope,
        "calibration_intercept": intercept,
        "calibration_in_the_large": calibration_in_the_large(y, p),
        "mean_predicted": float(p.mean()),
        "observed": float(y.mean()),
        "ece": expected_calibration_error(y, p),
        "ici": integrated_calibration_index(y, p),
        "reliability_curve": {
            "prob_pred": curve["prob_pred"].tolist(),
            "prob_true": curve["prob_true"].tolist(),
            "counts": curve["counts"].tolist(),
        },
    }
