"""Frozen constants for the feature-ablation and imputation audit.

The values here are part of the pre-registered protocol. Changing them after
results have been inspected turns the analysis into an exploratory one; record
any such change in the protocol changelog.
"""

from __future__ import annotations

PROTOCOL_VERSION = "1.0"
BASE_COMMIT = "db2bf514c37f27bfbae13ab79b559350bdcee970"
BASE_MODEL_SHA256 = "BC96BB1D7399391EA103C65515A76E5F40E8A7CFD4ACDCE27D59D935020C31F1"
BASE_MODEL_VERSION_PREFIX = "bc96bb1d"

FIVE_YEAR_DAYS = 1825
N_FOLDS = 5
PRIMARY_SEED = 42
REPEATED_SEEDS = tuple(range(42, 52))
N_BOOTSTRAP = 2000
N_OPTIMISM_RESAMPLES = 500
N_CALIBRATION_BINS = 10

MEANINGFUL_DELTA_AUC = 0.02
OVERFITTING_SLOPE_THRESHOLD = 0.80
MATERIAL_RANGE_PP = 0.10

RISK_BANDS = (
    ("low", 0.0, 0.15),
    ("moderate", 0.15, 0.40),
    ("high", 0.40, 1.0),
)
REPORT_THRESHOLDS = (0.15, 0.40, 0.50)
DECISION_THRESHOLDS = tuple(round(0.05 * i, 2) for i in range(1, 13))

ALL_FEATURES = (
    "trt",
    "age",
    "sex",
    "ascites",
    "hepato",
    "spiders",
    "edema",
    "bili",
    "chol",
    "albumin",
    "copper",
    "alk.phos",
    "ast",
    "trig",
    "platelet",
    "protime",
    "stage",
)

CORE_FIVE = ("age", "bili", "albumin", "protime", "edema")
F5 = CORE_FIVE
MAYO_FIVE = CORE_FIVE
F6 = (*CORE_FIVE, "sex")
F16 = tuple(feature for feature in ALL_FEATURES if feature != "trt")

FEATURE_SETS = {
    "F5": CORE_FIVE,
    "F6": F6,
    "F16": F16,
    "F17": ALL_FEATURES,
    "F17+IND": ALL_FEATURES,
}

OBSERVED_PATIENT_FIELDS = ("age", "bili", "albumin", "edema", "sex")
OPTIONAL_FEATURES = tuple(feature for feature in ALL_FEATURES if feature not in CORE_FIVE)
IMPUTED_OPTIONAL_FEATURES = tuple(
    feature for feature in ALL_FEATURES if feature not in OBSERVED_PATIENT_FIELDS
)
LEAKY_COLUMNS = ("id", "time", "status", "severe_event_5yr")
TARGET_COLUMN = "severe_event_5yr"
ID_COLUMN = "id"

PATIENT_B = {
    "age": 55.0,
    "sex": "f",
    "edema": 0.0,
    "bili": 1.0,
    "albumin": 3.5,
}

CLINICALLY_NORMAL_OPTIONAL = {
    "trt": 1.0,
    "ascites": 0.0,
    "hepato": 0.0,
    "spiders": 0.0,
    "chol": 180.0,
    "copper": 20.0,
    "alk.phos": 100.0,
    "ast": 25.0,
    "trig": 120.0,
    "platelet": 250.0,
    "protime": 10.5,
    "stage": 1.0,
}

# The public demo description and the deployed app both describe Patient B as
# a 55-year-old woman with these five observed values and all optional fields
# blank. The exact documented prediction is 27.4847%.
PATIENT_B_EXPECTED = 0.274846560155602

HOLDOUT_DERIVATION_COUNT = 312
HOLDOUT_VALIDATION_COUNT = 106
HOLDOUT_VALIDATION_LABELED = 72
HOLDOUT_VALIDATION_EVENTS = 34
HOLDOUT_MAYO_COMPLETE = 70
HOLDOUT_MAYO_EVENTS = 33

EXPECTED_COHORT_SIZE = 329
EXPECTED_EVENT_COUNT = 132
EXPECTED_NON_EVENT_COUNT = 197
EXPECTED_DROPPED_CENSORED = 89
