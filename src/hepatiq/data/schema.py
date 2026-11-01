"""Column contracts and validation for the canonical PBC cohorts.

These checks are deliberately explicit rather than schema-library based: the
contracts are small, the error messages are clinical, and validation must run
under the pinned Python version without pulling a heavy extra dependency.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from hepatiq.data.provenance import DataIntegrityError

PBC_COLUMNS = (
    "id",
    "time",
    "status",
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

PBCSEQ_COLUMNS = (
    "id",
    "futime",
    "status",
    "trt",
    "age",
    "sex",
    "day",
    "ascites",
    "hepato",
    "spiders",
    "edema",
    "bili",
    "chol",
    "albumin",
    "alk.phos",
    "ast",
    "platelet",
    "protime",
    "stage",
)

UDCA_COLUMNS = (
    "id",
    "trt",
    "entry.dt",
    "last.dt",
    "stage",
    "bili",
    "riskscore",
    "death.dt",
    "tx.dt",
    "hprogress.dt",
    "varices.dt",
    "ascites.dt",
    "enceph.dt",
    "double.dt",
    "worsen.dt",
)

UDCA1_COLUMNS = ("id", "trt", "stage", "bili", "riskscore", "futime", "status")
UDCA2_COLUMNS = (*UDCA1_COLUMNS, "endpoint")

EXPECTED_SHAPES = {
    "pbc": (418, len(PBC_COLUMNS)),
    "pbcseq": (1945, len(PBCSEQ_COLUMNS)),
    "udca": (170, len(UDCA_COLUMNS)),
    "udca1": (170, len(UDCA1_COLUMNS)),
    "udca2": (1360, len(UDCA2_COLUMNS)),
}

# The Mayo trial randomized 312 of the 418 recorded patients.
RANDOMIZED_PATIENTS = 312

# Patient 151 has zero follow-up and no stored riskscore; exclude it from
# survival benchmarks (leaving n = 169) rather than treating it as an event.
UDCA_ZERO_FOLLOWUP_IDS = (151,)


def require_columns(frame: pd.DataFrame, required: Iterable[str], name: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise DataIntegrityError(f"{name} is missing required columns: {missing}")


def require_shape(frame: pd.DataFrame, expected: tuple[int, int], name: str) -> None:
    if frame.shape != expected:
        raise DataIntegrityError(
            f"{name} has shape {frame.shape}, expected {expected}. "
            "The file may be edited or from another source."
        )


def require_unique_ids(frame: pd.DataFrame, name: str) -> None:
    duplicated = frame.loc[frame["id"].duplicated(), "id"].tolist()
    if duplicated:
        raise DataIntegrityError(f"{name} has duplicate patient ids: {duplicated[:10]}")


def validate_pbc(frame: pd.DataFrame) -> pd.DataFrame:
    require_columns(frame, PBC_COLUMNS, "pbc")
    require_shape(frame, EXPECTED_SHAPES["pbc"], "pbc")
    require_unique_ids(frame, "pbc")
    if not frame["status"].isin([0, 1, 2]).all():
        raise DataIntegrityError("pbc.status must be 0 (censored), 1 (transplant) or 2 (death)")
    treated = frame["trt"].dropna()
    if not treated.isin([1, 2]).all():
        raise DataIntegrityError("pbc.trt must be 1 (D-penicillamine) or 2 (placebo)")
    if treated.shape[0] != RANDOMIZED_PATIENTS:
        raise DataIntegrityError(
            f"pbc has {treated.shape[0]} randomized patients, expected {RANDOMIZED_PATIENTS}"
        )
    return frame


def validate_pbcseq(frame: pd.DataFrame) -> pd.DataFrame:
    require_columns(frame, PBCSEQ_COLUMNS, "pbcseq")
    require_shape(frame, EXPECTED_SHAPES["pbcseq"], "pbcseq")
    if frame["id"].nunique() != RANDOMIZED_PATIENTS:
        raise DataIntegrityError(
            f"pbcseq has {frame['id'].nunique()} patients, expected {RANDOMIZED_PATIENTS}"
        )
    if (frame["day"] < 0).any():
        raise DataIntegrityError("pbcseq.day must be non-negative")
    if (frame["day"] > frame["futime"]).any():
        raise DataIntegrityError("pbcseq has visits after the recorded follow-up time (day > futime)")
    if not frame["status"].isin([0, 1, 2]).all():
        raise DataIntegrityError("pbcseq.status must be 0, 1 or 2")
    return frame


def validate_udca(frame: pd.DataFrame) -> pd.DataFrame:
    require_columns(frame, UDCA_COLUMNS, "udca")
    require_shape(frame, EXPECTED_SHAPES["udca"], "udca")
    require_unique_ids(frame, "udca")
    if not frame["trt"].isin([0, 1]).all():
        raise DataIntegrityError("udca.trt must be 0 (placebo) or 1 (UDCA)")
    return frame


def validate_udca1(frame: pd.DataFrame) -> pd.DataFrame:
    require_columns(frame, UDCA1_COLUMNS, "udca1")
    require_shape(frame, EXPECTED_SHAPES["udca1"], "udca1")
    require_unique_ids(frame, "udca1")
    if not frame["status"].isin([0, 1]).all():
        raise DataIntegrityError("udca1.status must be 0 (censored) or 1 (event)")
    if (frame["futime"] < 0).any():
        raise DataIntegrityError("udca1.futime must be non-negative")
    zero_followup = frame["futime"] == 0
    if (zero_followup & (frame["status"] != 0)).any():
        raise DataIntegrityError("udca1 rows with zero follow-up must be censored")
    zero_ids = tuple(sorted(frame.loc[zero_followup, "id"].tolist()))
    if zero_ids != UDCA_ZERO_FOLLOWUP_IDS:
        raise DataIntegrityError(
            f"udca1 zero-follow-up ids changed: {zero_ids} (expected {UDCA_ZERO_FOLLOWUP_IDS})"
        )
    return frame


def validate_udca2(frame: pd.DataFrame) -> pd.DataFrame:
    require_columns(frame, UDCA2_COLUMNS, "udca2")
    require_shape(frame, EXPECTED_SHAPES["udca2"], "udca2")
    return frame


def validate_alignment(pbc: pd.DataFrame, pbcseq: pd.DataFrame) -> None:
    """`pbcseq` must describe a subset of the `pbc` patients, never new people."""
    extra = sorted(set(pbcseq["id"]) - set(pbc["id"]))
    if extra:
        raise DataIntegrityError(f"pbcseq contains ids absent from pbc: {extra[:10]}")
