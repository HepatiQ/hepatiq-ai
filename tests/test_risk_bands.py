"""Shared risk-band thresholds: boundaries are inclusive and consistent."""

import pytest

from hepatiq.risk_bands import HIGH_RISK_THRESHOLD, LOW_RISK_THRESHOLD, risk_category


@pytest.mark.parametrize(
    "probability,expected",
    [
        (0.0, "low"),
        (0.149999, "low"),
        (LOW_RISK_THRESHOLD, "intermediate"),
        (0.399999, "intermediate"),
        (HIGH_RISK_THRESHOLD, "high"),
        (1.0, "high"),
    ],
)
def test_risk_category_boundaries(probability, expected):
    assert risk_category(probability) == expected
