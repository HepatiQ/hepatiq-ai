"""Cohort, fold and pipeline guards for leakage-free research."""

import inspect
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from hepatiq.paths import EXTERNAL_PBC
from hepatiq.research.ablation import make_pipeline
from hepatiq.research.config import (
    ALL_FEATURES,
    EXPECTED_COHORT_SIZE,
    EXPECTED_EVENT_COUNT,
    FIVE_YEAR_DAYS,
    HOLDOUT_MAYO_COMPLETE,
    HOLDOUT_MAYO_EVENTS,
    HOLDOUT_VALIDATION_EVENTS,
    LEAKY_COLUMNS,
    PRIMARY_SEED,
)
from hepatiq.research.data import (
    five_year_labels,
    fold_assignments,
    heldout_indices,
    load_research_cohort,
    select_features,
)


def test_research_loader_uses_external_418_patient_file():
    signature = inspect.signature(load_research_cohort)
    assert Path(signature.parameters["path"].default) == EXTERNAL_PBC


def test_cohort_counts_and_feature_contract():
    cohort = load_research_cohort()
    assert cohort.n == EXPECTED_COHORT_SIZE
    assert cohort.n_events == EXPECTED_EVENT_COUNT
    assert tuple(cohort.features.columns) == ALL_FEATURES
    assert not set(LEAKY_COLUMNS).intersection(cohort.features.columns)
    assert cohort.ids.is_unique


def test_target_definition_matches_no_boundary_rows():
    frame = pd.read_csv(EXTERNAL_PBC)
    labels = five_year_labels(frame)
    assert labels.notna().sum() == EXPECTED_COHORT_SIZE
    assert int(labels.sum()) == EXPECTED_EVENT_COUNT
    assert not (frame["time"] == FIVE_YEAR_DAYS).any()


def test_feature_selection_rejects_leaky_or_unknown_columns():
    cohort = load_research_cohort()
    with pytest.raises(ValueError, match="leaky"):
        select_features(cohort.features, ("age", "time"))
    with pytest.raises(ValueError, match="unknown"):
        select_features(cohort.features, ("age", "not_a_feature"))


def test_fold_assignments_are_deterministic_and_complete():
    cohort = load_research_cohort()
    first = fold_assignments(cohort.target, seed=PRIMARY_SEED)
    second = fold_assignments(cohort.target, seed=PRIMARY_SEED)
    assert np.array_equal(first, second)
    assert set(first) == set(range(5))
    assert len(first) == cohort.n


def test_heldout_raw_split_is_312_and_106():
    raw = pd.read_csv(EXTERNAL_PBC)
    assert int(raw["trt"].notna().sum()) == 312
    assert int(raw["trt"].isna().sum()) == 106

    cohort = load_research_cohort()
    derivation, validation = heldout_indices(cohort.frame)
    assert len(derivation) == 257
    assert len(validation) == 72
    assert int(cohort.target.loc[validation].sum()) == HOLDOUT_VALIDATION_EVENTS
    assert HOLDOUT_MAYO_COMPLETE == 70
    assert HOLDOUT_MAYO_EVENTS == 33
    assert set(derivation).isdisjoint(set(validation))


def test_preprocessing_lives_inside_the_pipeline():
    pipeline = make_pipeline("lr", weighted=True, seed=PRIMARY_SEED)
    assert "preprocess" in pipeline.named_steps
    assert "scaler" in pipeline.named_steps
    assert "clf" in pipeline.named_steps
