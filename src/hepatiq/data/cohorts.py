"""Build the v2 survival and 12-month landmark cohorts.

The v1 pipeline drops patients censored before five years. The v2 data contract
keeps the full time-to-event outcome and adds a landmark cohort built only from
measurements recorded at or before day 365.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from hepatiq.data import schema
from hepatiq.data.build_tables import STATUS_LABELS, load_pbc, load_pbcseq
from hepatiq.data.provenance import DataIntegrityError, verify_datasets

LANDMARK_DAY = 365
SURVIVAL_DURATION_COLUMN = "duration_days"
SURVIVAL_EVENT_COLUMN = "event"
LANDMARK_CHOL_COLUMN = "chol_pre_landmark"

SURVIVAL_FEATURES = tuple(
    column for column in schema.PBC_COLUMNS if column not in {"id", "time", "status"}
)

LANDMARK_TIME_VARYING_FEATURES = (
    "ascites",
    "hepato",
    "spiders",
    "edema",
    "bili",
    "albumin",
    "alk.phos",
    "ast",
    "platelet",
    "protime",
    "stage",
)

DEFAULT_LANDMARK_FEATURES = (
    "trt",
    "age",
    "sex",
    *LANDMARK_TIME_VARYING_FEATURES,
)

OPTIONAL_LANDMARK_FEATURES = (LANDMARK_CHOL_COLUMN,)

_EXPECTED_SURVIVAL = (418, 186, 232, 312)
_EXPECTED_LANDMARK = (254, 110, 144)
_EXPECTED_LANDMARK_CHOL_MISSING = 195


def _validate_baseline_frame(frame: pd.DataFrame) -> None:
    schema.require_columns(frame, schema.PBC_COLUMNS, "pbc")
    if frame["id"].duplicated().any():
        raise DataIntegrityError("pbc has duplicate patient ids")
    if frame["time"].isna().any() or (frame["time"] <= 0).any():
        raise DataIntegrityError("pbc.time must be positive and non-missing")
    if not frame["status"].isin([0, 1, 2]).all():
        raise DataIntegrityError("pbc.status must be 0 (censored), 1 (transplant) or 2 (death)")


def _validate_pbcseq_frame(frame: pd.DataFrame) -> None:
    schema.require_columns(frame, schema.PBCSEQ_COLUMNS, "pbcseq")
    if frame["id"].isna().any():
        raise DataIntegrityError("pbcseq.id must be non-missing")
    if frame["day"].isna().any() or (frame["day"] < 0).any():
        raise DataIntegrityError("pbcseq.day must be non-negative and non-missing")
    if not frame["status"].isin([0, 1, 2]).all():
        raise DataIntegrityError("pbcseq.status must be 0, 1 or 2")


def _require_counts(label: str, observed: tuple[int, ...], expected: tuple[int, ...]) -> None:
    if observed != expected:
        raise DataIntegrityError(f"{label} mismatch: observed {observed}, expected {expected}")


def build_survival_cohort(
    pbc: pd.DataFrame | None = None,
    *,
    verify_provenance: bool = True,
) -> pd.DataFrame:
    """Return the v2 time-to-event cohort with censoring preserved.

    ``event`` is death or transplant; ``duration_days`` is the recorded
    follow-up time. All 418 canonical patients are retained, including the 106
    non-randomized patients whose ``trt`` is missing.
    """
    if verify_provenance:
        verify_datasets()

    frame = load_pbc() if pbc is None else pbc.copy()
    frame = frame.reset_index(drop=True)
    _validate_baseline_frame(frame)

    observed = (
        len(frame),
        int(frame["status"].isin([1, 2]).sum()),
        int((frame["status"] == 0).sum()),
        int(frame["trt"].notna().sum()),
    )
    _require_counts("survival cohort", observed, _EXPECTED_SURVIVAL)

    cohort = pd.DataFrame(
        {
            "id": frame["id"].to_numpy(),
            SURVIVAL_DURATION_COLUMN: frame["time"].to_numpy(),
            SURVIVAL_EVENT_COLUMN: (frame["status"] != 0).astype("int8").to_numpy(),
            "event_type": frame["status"].map(STATUS_LABELS).to_numpy(),
            "randomized": frame["trt"].notna().to_numpy(),
        }
    )
    for feature in SURVIVAL_FEATURES:
        cohort[feature] = frame[feature].to_numpy()

    return cohort.sort_values("id").reset_index(drop=True)


def build_landmark_cohort(
    landmark_day: int = LANDMARK_DAY,
    pbc: pd.DataFrame | None = None,
    pbcseq: pd.DataFrame | None = None,
    *,
    verify_provenance: bool = True,
) -> pd.DataFrame:
    """Return the 12-month landmark cohort from pre-landmark visits only.

    Eligibility requires a visit at or after ``landmark_day``. Features come
    from the latest visit at or before the landmark; every later visit is
    excluded before the feature frame is assembled. ``chol`` is retained as
    ``chol_pre_landmark`` for auditability but is not a default feature because
    it is missing for most eligible patients.
    """
    if isinstance(landmark_day, bool) or not isinstance(landmark_day, int) or landmark_day <= 0:
        raise ValueError("landmark_day must be a positive integer")

    if verify_provenance:
        verify_datasets()

    baseline = load_pbc() if pbc is None else pbc.copy()
    sequential = load_pbcseq() if pbcseq is None else pbcseq.copy()
    baseline = baseline.reset_index(drop=True)
    sequential = sequential.reset_index(drop=True)

    _validate_baseline_frame(baseline)
    _validate_pbcseq_frame(sequential)
    schema.validate_alignment(baseline, sequential)

    max_day = sequential.groupby("id")["day"].max()
    eligible_ids = max_day[max_day >= landmark_day].index
    if len(eligible_ids) == 0:
        raise DataIntegrityError(f"no patients have a visit at or after day {landmark_day}")

    pre_landmark = sequential.loc[
        sequential["day"].le(landmark_day) & sequential["id"].isin(eligible_ids)
    ].copy()
    latest = (
        pre_landmark.sort_values(["id", "day"], kind="mergesort")
        .groupby("id", sort=True)
        .tail(1)
        .sort_values("id")
        .reset_index(drop=True)
    )
    if latest["id"].duplicated().any():
        raise DataIntegrityError("landmark cohort contains duplicate patient ids")
    if set(latest["id"]) != set(eligible_ids):
        raise DataIntegrityError("not every eligible patient has a pre-landmark visit")

    static = baseline.set_index("id").reindex(latest["id"])
    if static["time"].isna().any():
        raise DataIntegrityError("landmark cohort contains ids absent from pbc")

    durations = static["time"].to_numpy() - landmark_day
    if (durations <= 0).any():
        raise DataIntegrityError("landmark cohort contains non-positive post-landmark follow-up")

    visits = pre_landmark.groupby("id").size().reindex(latest["id"]).astype(int).to_numpy()
    cohort = pd.DataFrame(
        {
            "id": latest["id"].to_numpy(),
            SURVIVAL_DURATION_COLUMN: durations,
            SURVIVAL_EVENT_COLUMN: (static["status"] != 0).astype("int8").to_numpy(),
            "event_type": static["status"].map(STATUS_LABELS).to_numpy(),
            "trt": static["trt"].to_numpy(),
            "age": static["age"].to_numpy(),
            "sex": static["sex"].to_numpy(),
            "last_visit_day": latest["day"].to_numpy(),
            "visit_gap_days": landmark_day - latest["day"].to_numpy(),
            "n_visits_pre_landmark": visits,
        }
    )
    for feature in LANDMARK_TIME_VARYING_FEATURES:
        cohort[feature] = latest[feature].to_numpy()
    cohort[LANDMARK_CHOL_COLUMN] = latest["chol"].to_numpy()

    if (cohort["last_visit_day"] > landmark_day).any():
        raise DataIntegrityError("landmark feature frame contains a post-landmark visit")
    if (cohort["last_visit_day"] + cohort["visit_gap_days"] != landmark_day).any():
        raise DataIntegrityError("landmark visit-gap accounting is inconsistent")
    if not set(DEFAULT_LANDMARK_FEATURES).issubset(cohort.columns):
        raise DataIntegrityError("landmark cohort is missing a default feature")
    if LANDMARK_CHOL_COLUMN in DEFAULT_LANDMARK_FEATURES:
        raise DataIntegrityError("chol_pre_landmark must not be a default landmark feature")

    if landmark_day == LANDMARK_DAY:
        observed = (
            len(cohort),
            int(cohort[SURVIVAL_EVENT_COLUMN].sum()),
            int((cohort[SURVIVAL_EVENT_COLUMN] == 0).sum()),
        )
        _require_counts("landmark cohort", observed, _EXPECTED_LANDMARK)
        chol_missing = int(cohort[LANDMARK_CHOL_COLUMN].isna().sum())
        if chol_missing != _EXPECTED_LANDMARK_CHOL_MISSING:
            raise DataIntegrityError(
                "landmark chol missingness changed: "
                f"observed {chol_missing}, expected {_EXPECTED_LANDMARK_CHOL_MISSING}"
            )

    return cohort.sort_values("id").reset_index(drop=True)


def cohort_manifest(
    pbc: pd.DataFrame | None = None,
    pbcseq: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Return the source hashes, counts and contracts for the v2 cohorts."""
    datasets = verify_datasets()
    survival = build_survival_cohort(pbc, verify_provenance=False)
    landmark = build_landmark_cohort(
        LANDMARK_DAY,
        pbc,
        pbcseq,
        verify_provenance=False,
    )

    return {
        "schema_version": 1,
        "sources": {
            name: {
                "file": datasets[name]["file"],
                "sha256": datasets[name]["sha256"],
                "rows": datasets[name]["rows"],
            }
            for name in ("pbc", "pbcseq")
        },
        "survival": {
            "definition": "time to death or transplant; censoring preserved",
            "rows": int(len(survival)),
            "events": int(survival[SURVIVAL_EVENT_COLUMN].sum()),
            "censored": int((survival[SURVIVAL_EVENT_COLUMN] == 0).sum()),
            "randomized": int(survival["randomized"].sum()),
            "features": list(SURVIVAL_FEATURES),
        },
        "landmark": {
            "definition": "12-month landmark; features at or before day 365",
            "landmark_day": LANDMARK_DAY,
            "rows": int(len(landmark)),
            "events": int(landmark[SURVIVAL_EVENT_COLUMN].sum()),
            "censored": int((landmark[SURVIVAL_EVENT_COLUMN] == 0).sum()),
            "chol_missing": int(landmark[LANDMARK_CHOL_COLUMN].isna().sum()),
            "default_features": list(DEFAULT_LANDMARK_FEATURES),
            "optional_features": list(OPTIONAL_LANDMARK_FEATURES),
        },
    }
