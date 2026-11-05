"""Discrimination-only comparison with the Mayo Risk Score, never a probability."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from hepatiq.research.config import N_BOOTSTRAP, TARGET_COLUMN
from hepatiq.risk.mayo_risk_score import mayo_risk_score_series


def mayo_scores(frame: pd.DataFrame) -> pd.Series:
    return mayo_risk_score_series(frame)


def common_patient_mask(frame: pd.DataFrame, mayo: pd.Series) -> np.ndarray:
    if TARGET_COLUMN not in frame.columns:
        raise ValueError(f"frame must contain {TARGET_COLUMN}")
    return np.isfinite(mayo.to_numpy(dtype=float)) & frame[TARGET_COLUMN].notna().to_numpy()


def _auc_ci(y: np.ndarray, scores: np.ndarray, n_boot: int, seed: int) -> dict[str, float | int]:
    point = float(roc_auc_score(y, scores))
    rng = np.random.RandomState(seed)
    values: list[float] = []
    for _ in range(n_boot):
        idx = rng.randint(0, len(y), len(y))
        if len(np.unique(y[idx])) < 2:
            continue
        values.append(float(roc_auc_score(y[idx], scores[idx])))
    if not values:
        return {"point": point, "lower": float("nan"), "upper": float("nan"), "n_valid": 0}
    lower, upper = np.percentile(values, [2.5, 97.5])
    return {"point": point, "lower": float(lower), "upper": float(upper), "n_valid": len(values)}


def _paired_auc_difference(
    y: np.ndarray,
    hep: np.ndarray,
    mayo: np.ndarray,
    n_boot: int,
    seed: int,
) -> dict[str, float | int]:
    point = float(roc_auc_score(y, hep) - roc_auc_score(y, mayo))
    rng = np.random.RandomState(seed)
    diffs: list[float] = []
    for _ in range(n_boot):
        idx = rng.randint(0, len(y), len(y))
        if len(np.unique(y[idx])) < 2:
            continue
        diffs.append(float(roc_auc_score(y[idx], hep[idx]) - roc_auc_score(y[idx], mayo[idx])))
    if not diffs:
        return {"point": point, "lower": float("nan"), "upper": float("nan"), "p_value": float("nan")}
    values = np.asarray(diffs)
    lower, upper = np.percentile(values, [2.5, 97.5])
    p_value = min(1.0, 2.0 * min(float(np.mean(values <= 0)), float(np.mean(values >= 0))))
    return {"point": point, "lower": float(lower), "upper": float(upper), "p_value": p_value}


def compare_discrimination(
    frame: pd.DataFrame,
    hepatiq_probabilities: np.ndarray,
    *,
    n_boot: int = N_BOOTSTRAP,
    seed: int = 42,
) -> dict[str, object]:
    """AUC comparison on patients with a complete Mayo score and a known label.

    The Mayo Risk Score is a linear score, not a probability, so only rank-based
    discrimination is compared here.
    """
    probabilities = np.asarray(hepatiq_probabilities, dtype=float)
    if len(probabilities) != len(frame):
        raise ValueError("hepatiq_probabilities must align with frame rows")

    scores = mayo_scores(frame)
    mask = common_patient_mask(frame, scores)
    y = frame.loc[mask, TARGET_COLUMN].to_numpy(dtype=float)
    mrs = scores.loc[mask].to_numpy(dtype=float)
    hep = probabilities[mask]

    return {
        "n": int(mask.sum()),
        "events": int(y.sum()),
        "mayo_auc": _auc_ci(y, mrs, n_boot, seed),
        "hepatiq_auc": _auc_ci(y, hep, n_boot, seed),
        "delta_auc_hepatiq_minus_mayo": _paired_auc_difference(y, hep, mrs, n_boot, seed),
        "probability_comparison": "blocked: Mayo baseline survival function is not in the repository",
    }
