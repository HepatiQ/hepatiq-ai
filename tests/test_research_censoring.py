"""Censoring-bound and death-only sensitivity helpers."""

import pandas as pd

from hepatiq.paths import EXTERNAL_PBC
from hepatiq.research.censoring import (
    bound_summary,
    death_only_labels,
    death_only_summary,
    labels_with_censoring,
)


def test_bounds_match_the_frozen_cohort():
    frame = pd.read_csv(EXTERNAL_PBC)
    summary = bound_summary(frame)
    assert summary["n_total"] == 418
    assert summary["labeled"] == 329
    assert summary["censored_before_5y"] == 89
    assert summary["primary_events"] == 132
    assert summary["best_case_events"] == 132
    assert summary["worst_case_events"] == 221


def test_censoring_labels_cover_every_row_and_only_use_0_1():
    frame = pd.read_csv(EXTERNAL_PBC)
    best = labels_with_censoring(frame, 0)
    worst = labels_with_censoring(frame, 1)
    assert set(best.unique()).issubset({0, 1})
    assert set(worst.unique()).issubset({0, 1})
    assert len(best) == len(worst) == len(frame)


def test_death_only_endpoint_drops_transplants_and_censoring():
    frame = pd.read_csv(EXTERNAL_PBC)
    labels = death_only_labels(frame)
    summary = death_only_summary(frame)
    assert labels.notna().sum() == 312
    assert summary["deaths"] == 115
    assert summary["dropped_transplant_or_censored"] == 106
