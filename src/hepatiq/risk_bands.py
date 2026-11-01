"""Single source of truth for risk-band thresholds and categories.

Thresholds are descriptive communication aids, not clinical action thresholds.
"""

from typing import Literal

LOW_RISK_THRESHOLD = 0.15
HIGH_RISK_THRESHOLD = 0.40

RiskBand = Literal["low", "intermediate", "high"]


def risk_category(probability: float) -> RiskBand:
    """Map a predicted probability to the shared low/intermediate/high band."""
    if probability >= HIGH_RISK_THRESHOLD:
        return "high"
    if probability >= LOW_RISK_THRESHOLD:
        return "intermediate"
    return "low"
