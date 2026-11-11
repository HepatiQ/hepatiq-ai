"""Contract tests for the v2 survival and 12-month landmark cohorts."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hepatiq.data import (
    DEFAULT_LANDMARK_FEATURES,
    LANDMARK_CHOL_COLUMN,
    LANDMARK_DAY,
    DataIntegrityError,
    build_landmark_cohort,
    build_survival_cohort,
    cohort_manifest,
    load_pbc,
    load_pbcseq,
    verify_datasets,
)
from hepatiq.paths import EXTERNAL_PBC


def test_survival_cohort_contract() -> None:
    cohort = build_survival_cohort()

    assert len(cohort) == 418
    assert cohort["id"].is_unique
    assert int(cohort["event"].sum()) == 186
    assert int((cohort["event"] == 0).sum()) == 232
    assert int(cohort["randomized"].sum()) == 312
    assert int(cohort["trt"].isna().sum()) == 106
    assert set(cohort["event_type"]) == {"censored", "transplant", "death"}
    assert (cohort["duration_days"] > 0).all()
    assert not {"time", "status"}.intersection(cohort.columns)


def test_landmark_cohort_contract() -> None:
    cohort = build_landmark_cohort()

    assert len(cohort) == 254
    assert int(cohort["event"].sum()) == 110
    assert int((cohort["event"] == 0).sum()) == 144
    assert (cohort["duration_days"] > 0).all()
    assert cohort["last_visit_day"].le(LANDMARK_DAY).all()
    assert (cohort["last_visit_day"] + cohort["visit_gap_days"] == LANDMARK_DAY).all()
    assert cohort["n_visits_pre_landmark"].ge(1).all()
    assert int(cohort[LANDMARK_CHOL_COLUMN].isna().sum()) == 195
    assert LANDMARK_CHOL_COLUMN not in DEFAULT_LANDMARK_FEATURES
    assert set(DEFAULT_LANDMARK_FEATURES).issubset(cohort.columns)
    assert not {"time", "status", "futime", "day"}.intersection(cohort.columns)


def test_landmark_eligibility_and_pre_landmark_visit_selection() -> None:
    cohort = build_landmark_cohort()
    sequential = load_pbcseq()

    max_day = sequential.groupby("id")["day"].max()
    expected_ids = set(max_day[max_day >= LANDMARK_DAY].index)
    assert set(cohort["id"]) == expected_ids

    expected_last = sequential.loc[sequential["day"].le(LANDMARK_DAY)].groupby("id")["day"].max()
    observed_last = expected_last.reindex(cohort["id"]).to_numpy()
    np.testing.assert_array_equal(cohort["last_visit_day"].to_numpy(), observed_last)


def test_landmark_outcome_uses_baseline_followup_after_landmark() -> None:
    cohort = build_landmark_cohort()
    baseline = load_pbc().set_index("id")
    static = baseline.loc[cohort["id"]]

    np.testing.assert_array_equal(
        cohort["duration_days"].to_numpy(),
        static["time"].to_numpy() - LANDMARK_DAY,
    )
    np.testing.assert_array_equal(
        cohort["event"].to_numpy(),
        (static["status"] != 0).astype("int8").to_numpy(),
    )


def test_cohort_manifest_records_sources_and_counts() -> None:
    manifest = cohort_manifest()
    datasets = verify_datasets()

    assert manifest["sources"]["pbc"]["sha256"] == datasets["pbc"]["sha256"]
    assert manifest["sources"]["pbcseq"]["sha256"] == datasets["pbcseq"]["sha256"]
    assert manifest["survival"]["rows"] == 418
    assert manifest["survival"]["events"] == 186
    assert manifest["survival"]["randomized"] == 312
    assert manifest["landmark"]["rows"] == 254
    assert manifest["landmark"]["events"] == 110
    assert manifest["landmark"]["chol_missing"] == 195


def test_cohort_builders_are_deterministic() -> None:
    pd.testing.assert_frame_equal(build_survival_cohort(), build_survival_cohort())
    pd.testing.assert_frame_equal(build_landmark_cohort(), build_landmark_cohort())


def test_landmark_rejects_non_positive_landmark_day() -> None:
    with pytest.raises(ValueError, match="landmark_day"):
        build_landmark_cohort(landmark_day=0)


def test_survival_rejects_non_canonical_cohort() -> None:
    partial = pd.read_csv(EXTERNAL_PBC).head(10)
    with pytest.raises(DataIntegrityError, match="survival cohort mismatch"):
        build_survival_cohort(partial, verify_provenance=False)
