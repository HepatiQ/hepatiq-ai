"""Mayo Risk Score for primary biliary cholangitis (Dickson et al., 1989).

    R = 0.871 ln(bilirubin) - 2.53 ln(albumin) + 0.039 age
        + 2.38 ln(prothrombin time) + 2.33 edema

Units: bilirubin mg/dL, albumin g/dL, prothrombin time seconds, age years,
edema coded 0 (none), 0.5 (controlled with diuretics) or 1 (despite diuretics).
Higher scores mean higher risk. This is a *score*, not a probability; the
published baseline survival function is required to turn it into a 5-year
survival estimate, which is why v2 benchmarks discrimination first and defers
calibration to the calibration phase.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

COEFFICIENTS = {
    "ln_bili": 0.871,
    "ln_albumin": -2.53,
    "age": 0.039,
    "ln_protime": 2.38,
    "edema": 2.33,
}

VALID_EDEMA = {0.0, 0.5, 1.0}


class MayoRiskScoreInputError(ValueError):
    """Raised when a Mayo Risk Score input is outside its physiological domain."""


def _validate_scalar(age: float, bili: float, albumin: float, protime: float, edema: float) -> None:
    if not np.isfinite([age, bili, albumin, protime, edema]).all():
        raise MayoRiskScoreInputError("Mayo Risk Score inputs must be finite")
    if age <= 0:
        raise MayoRiskScoreInputError(f"age must be positive, got {age}")
    if bili <= 0:
        raise MayoRiskScoreInputError(f"bilirubin must be positive, got {bili}")
    if albumin <= 0:
        raise MayoRiskScoreInputError(f"albumin must be positive, got {albumin}")
    if protime <= 0:
        raise MayoRiskScoreInputError(f"prothrombin time must be positive, got {protime}")
    if edema not in VALID_EDEMA:
        raise MayoRiskScoreInputError(f"edema must be one of {sorted(VALID_EDEMA)}, got {edema}")


def mayo_risk_score(*, age: float, bili: float, albumin: float, protime: float, edema: float) -> float:
    """Compute one Mayo Risk Score with domain validation."""
    _validate_scalar(age, bili, albumin, protime, edema)
    return float(
        COEFFICIENTS["ln_bili"] * np.log(bili)
        + COEFFICIENTS["ln_albumin"] * np.log(albumin)
        + COEFFICIENTS["age"] * age
        + COEFFICIENTS["ln_protime"] * np.log(protime)
        + COEFFICIENTS["edema"] * edema
    )


def mayo_risk_score_series(frame: pd.DataFrame, *, strict: bool = True) -> pd.Series:
    """Vectorised Mayo Risk Score for a frame with the five required columns.

    Rows with any missing input get ``NaN``. With ``strict=True`` (default) any
    present but invalid value raises instead of silently producing ``NaN``.
    """
    required = ("age", "bili", "albumin", "protime", "edema")
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise MayoRiskScoreInputError(f"missing columns: {missing}")

    values = frame[list(required)].astype(float)
    present = values.notna().all(axis=1)

    if strict and present.any():
        subset = values[present]
        invalid: list[str] = []
        if (subset["age"] <= 0).any():
            invalid.append("age <= 0")
        if (subset["bili"] <= 0).any():
            invalid.append("bili <= 0")
        if (subset["albumin"] <= 0).any():
            invalid.append("albumin <= 0")
        if (subset["protime"] <= 0).any():
            invalid.append("protime <= 0")
        if not subset["edema"].isin(VALID_EDEMA).all():
            invalid.append("edema not in {0, 0.5, 1}")
        if invalid:
            raise MayoRiskScoreInputError(f"invalid Mayo Risk Score inputs: {invalid}")

    score = (
        COEFFICIENTS["ln_bili"] * np.log(values["bili"])
        + COEFFICIENTS["ln_albumin"] * np.log(values["albumin"])
        + COEFFICIENTS["age"] * values["age"]
        + COEFFICIENTS["ln_protime"] * np.log(values["protime"])
        + COEFFICIENTS["edema"] * values["edema"]
    )
    score[~present] = np.nan
    return score.rename("mayo_risk_score")
