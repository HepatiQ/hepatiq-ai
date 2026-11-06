"""DATA-01 guards: the canonical cohort is the single training source."""

import inspect
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from hepatiq.data import DataIntegrityError
from hepatiq.ml import build_5yr_target as target_module
from hepatiq.ml.build_5yr_target import build_target
from hepatiq.paths import EXTERNAL_PBC, RAW_DATA


def _labeled_cohort(path: Path, *, verify_provenance: bool) -> pd.DataFrame:
    return (
        build_target(str(path), verify_provenance=verify_provenance)
        .sort_values("id")
        .reset_index(drop=True)
    )


def test_canonical_and_archived_raw_cohorts_have_the_same_labels():
    raw = _labeled_cohort(RAW_DATA, verify_provenance=False)
    canonical = _labeled_cohort(EXTERNAL_PBC, verify_provenance=True)

    assert len(raw) == len(canonical) == 329
    assert int(raw["severe_event_5yr"].sum()) == 132
    assert raw["id"].tolist() == canonical["id"].tolist()

    raw_age = raw.pop("age")
    canonical_age = canonical.pop("age")
    pd.testing.assert_frame_equal(raw, canonical, check_dtype=False)
    np.testing.assert_allclose(raw_age.to_numpy(), canonical_age.to_numpy(), rtol=0, atol=1e-6)


def test_build_target_defaults_to_canonical_and_verifies_before_reading(monkeypatch):
    calls = []
    real_verify = target_module.verify_datasets
    real_read = target_module.pd.read_csv

    monkeypatch.setattr(
        target_module,
        "verify_datasets",
        lambda: calls.append("verify") or real_verify(),
    )
    monkeypatch.setattr(
        target_module.pd,
        "read_csv",
        lambda path: calls.append(("read", str(path))) or real_read(path),
    )

    frame = build_target()

    assert len(frame) == 329
    assert calls == ["verify", ("read", str(EXTERNAL_PBC))]
    assert Path(inspect.signature(build_target).parameters["input_path"].default) == EXTERNAL_PBC


def test_build_target_aborts_when_provenance_fails(monkeypatch):
    def fail():
        raise DataIntegrityError("canonical pbc.csv does not match pinned hash")

    monkeypatch.setattr(target_module, "verify_datasets", fail)

    with pytest.raises(DataIntegrityError, match="does not match pinned"):
        build_target()
