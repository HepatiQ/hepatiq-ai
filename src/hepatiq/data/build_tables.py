"""Load the canonical PBC cohorts with validation applied at the boundary.

Every loader reads only from ``data/external`` (never ``data/raw``), validates
the column contract and shape, and raises ``DataIntegrityError`` with a
regeneration hint when a file is missing or has been edited.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from hepatiq import paths
from hepatiq.data import schema
from hepatiq.data.provenance import REGENERATE_HINT, DataIntegrityError, verify_datasets

STATUS_LABELS = {0: "censored", 1: "transplant", 2: "death"}
TRT_LABELS = {1: "D-penicillamine", 2: "placebo"}


def _read_csv(path: Path | str | None, default: Path, name: str) -> pd.DataFrame:
    resolved = Path(path) if path is not None else default
    if not resolved.exists():
        raise DataIntegrityError(f"Missing {name} dataset: {resolved}. {REGENERATE_HINT}")
    return pd.read_csv(resolved)


def load_pbc(path: Path | str | None = None, validate: bool = True) -> pd.DataFrame:
    """Load the 418-row baseline Mayo cohort.

    Adds convenience columns: ``event`` (death or transplant), ``death``,
    ``transplant``, ``status_label`` and ``trt_label``. ``trt`` stays nullable
    because 106 non-randomized patients have no treatment arm.
    """
    frame = _read_csv(path, paths.EXTERNAL_PBC, "pbc")
    if validate:
        schema.validate_pbc(frame)
    frame = frame.copy()
    frame["sex"] = frame["sex"].astype("string").str.lower()
    frame["event"] = (frame["status"] != 0).astype("int8")
    frame["death"] = (frame["status"] == 2).astype("int8")
    frame["transplant"] = (frame["status"] == 1).astype("int8")
    frame["status_label"] = frame["status"].map(STATUS_LABELS)
    frame["trt_label"] = frame["trt"].map(TRT_LABELS)
    return frame


def load_pbcseq(path: Path | str | None = None, validate: bool = True) -> pd.DataFrame:
    """Load the 1945-row serial follow-up table for the 312 randomized patients."""
    frame = _read_csv(path, paths.EXTERNAL_PBCSEQ, "pbcseq")
    if validate:
        schema.validate_pbcseq(frame)
    frame = frame.copy()
    frame["sex"] = frame["sex"].astype("string").str.lower()
    return frame


def load_udca(path: Path | str | None = None, validate: bool = True) -> pd.DataFrame:
    """Load the 170-patient UDCA trial with ISO date columns and stored riskscore."""
    frame = _read_csv(path, paths.EXTERNAL_UDCA, "udca")
    if validate:
        schema.validate_udca(frame)
    return frame


def load_udca1(path: Path | str | None = None, validate: bool = True) -> pd.DataFrame:
    """Load the one-row-per-patient UDCA survival table."""
    frame = _read_csv(path, paths.EXTERNAL_UDCA1, "udca1")
    if validate:
        schema.validate_udca1(frame)
    return frame


def load_udca2(path: Path | str | None = None, validate: bool = True) -> pd.DataFrame:
    """Load the multiple-endpoints-per-patient UDCA table."""
    frame = _read_csv(path, paths.EXTERNAL_UDCA2, "udca2")
    if validate:
        schema.validate_udca2(frame)
    return frame


def load_all(verify_integrity: bool = True) -> dict[str, pd.DataFrame]:
    """Load every external table, optionally asserting pinned SHA-256 hashes."""
    if verify_integrity:
        verify_datasets()
    tables = {
        "pbc": load_pbc(),
        "pbcseq": load_pbcseq(),
        "udca": load_udca(),
        "udca1": load_udca1(),
        "udca2": load_udca2(),
    }
    schema.validate_alignment(tables["pbc"], tables["pbcseq"])
    return tables


def dataset_summary() -> dict[str, dict[str, Any]]:
    """Return the provenance, row/column counts and hash for each dataset."""
    return verify_datasets()
