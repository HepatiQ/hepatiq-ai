"""Frozen protocol constants stay internally consistent."""

from hepatiq.research.config import (
    ALL_FEATURES,
    EXPECTED_COHORT_SIZE,
    EXPECTED_EVENT_COUNT,
    F5,
    F16,
    FEATURE_SETS,
    IMPUTED_OPTIONAL_FEATURES,
    LEAKY_COLUMNS,
    PATIENT_B_EXPECTED,
)


def test_feature_sets_are_frozen_and_ordered():
    assert FEATURE_SETS["F5"] == F5 == ("age", "bili", "albumin", "protime", "edema")
    assert FEATURE_SETS["F6"] == (*F5, "sex")
    assert "trt" not in F16
    assert len(FEATURE_SETS["F17"]) == 17
    assert FEATURE_SETS["F17"] == ALL_FEATURES
    assert FEATURE_SETS["F17+IND"] == ALL_FEATURES


def test_no_leaky_column_is_a_feature_or_optional_imputation_target():
    assert not set(LEAKY_COLUMNS).intersection(ALL_FEATURES)
    assert "sex" not in IMPUTED_OPTIONAL_FEATURES
    assert "protime" in IMPUTED_OPTIONAL_FEATURES
    assert set(IMPUTED_OPTIONAL_FEATURES) == set(ALL_FEATURES) - {
        "age",
        "bili",
        "albumin",
        "edema",
        "sex",
    }


def test_protocol_counts_and_documented_patient_b():
    assert (EXPECTED_COHORT_SIZE, EXPECTED_EVENT_COUNT) == (329, 132)
    assert 0.2748 < PATIENT_B_EXPECTED < 0.2749
