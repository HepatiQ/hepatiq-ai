from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hepatiq.data import load_pbc, load_udca1
from hepatiq.risk import (
    MayoRiskScoreInputError,
    albi_grade,
    albi_score,
    apri_score,
    benchmark_derivation_validation_split,
    benchmark_pbc,
    benchmark_udca_stored_score,
    five_year_outcome,
    harrell_c_index,
    mayo_risk_score,
    mayo_risk_score_series,
)


def test_mayo_risk_score_matches_hand_computation() -> None:
    score = mayo_risk_score(age=50.0, bili=1.0, albumin=4.0, protime=10.0, edema=0.0)
    assert score == pytest.approx(3.9228278, abs=1e-6)


def test_mayo_risk_score_edema_contribution() -> None:
    base = mayo_risk_score(age=50.0, bili=1.0, albumin=4.0, protime=10.0, edema=0.0)
    controlled = mayo_risk_score(age=50.0, bili=1.0, albumin=4.0, protime=10.0, edema=0.5)
    assert controlled - base == pytest.approx(1.165)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"age": 0.0, "bili": 1.0, "albumin": 4.0, "protime": 10.0, "edema": 0.0},
        {"age": 50.0, "bili": 0.0, "albumin": 4.0, "protime": 10.0, "edema": 0.0},
        {"age": 50.0, "bili": 1.0, "albumin": -1.0, "protime": 10.0, "edema": 0.0},
        {"age": 50.0, "bili": 1.0, "albumin": 4.0, "protime": 10.0, "edema": 0.25},
    ],
)
def test_mayo_risk_score_rejects_invalid_inputs(kwargs: dict[str, float]) -> None:
    with pytest.raises(MayoRiskScoreInputError):
        mayo_risk_score(**kwargs)


def test_mayo_risk_score_series_propagates_missing_and_checks_domain() -> None:
    frame = pd.DataFrame(
        {
            "age": [50.0, 60.0, 70.0],
            "bili": [1.0, np.nan, 2.0],
            "albumin": [4.0, 3.5, 3.0],
            "protime": [10.0, 11.0, 12.0],
            "edema": [0.0, 0.0, 1.0],
        }
    )
    scores = mayo_risk_score_series(frame)
    assert np.isfinite(scores.iloc[0])
    assert np.isnan(scores.iloc[1])
    assert np.isfinite(scores.iloc[2])

    frame.loc[0, "bili"] = -1.0
    with pytest.raises(MayoRiskScoreInputError):
        mayo_risk_score_series(frame)


def test_albi_and_apri_formulas() -> None:
    albi = albi_score(pd.Series([1.0]), pd.Series([4.0])).iloc[0]
    assert albi == pytest.approx(np.log10(17.1) * 0.66 - 3.4, abs=1e-9)
    grades = albi_grade(pd.Series([-2.7, -2.0, -1.0, np.nan]))
    assert grades.iloc[:3].tolist() == [1, 2, 3]
    assert np.isnan(grades.iloc[3])

    apri = apri_score(pd.Series([80.0]), pd.Series([150.0])).iloc[0]
    assert apri == pytest.approx(1.3333333, abs=1e-6)


def test_harrell_c_index_ordering_and_censoring() -> None:
    time = np.array([1.0, 2.0, 3.0])
    event = np.array([1, 1, 1])
    assert harrell_c_index(time, event, np.array([3.0, 2.0, 1.0])) == 1.0
    assert harrell_c_index(time, event, np.array([1.0, 2.0, 3.0])) == 0.0
    assert harrell_c_index(time, event, np.array([2.0, 2.0, 2.0])) == 0.5

    censored = np.array([1, 0, 1])
    assert harrell_c_index(time, censored, np.array([3.0, 1.0, 2.0])) == 1.0


def test_five_year_outcome_handles_censoring() -> None:
    time = np.array([1000.0, 2000.0, 2000.0, 1000.0])
    event = np.array([1, 1, 0, 0])
    labels = five_year_outcome(time, event)
    assert labels[0] == 1.0
    assert labels[1] == 0.0
    assert labels[2] == 0.0
    assert np.isnan(labels[3])


def test_pbc_benchmark_runs_and_scores_discriminate() -> None:
    rows = benchmark_pbc(load_pbc(), n_boot=80)
    by_name = {row["score"]: row for row in rows}
    assert len(rows) == 5
    assert by_name["Mayo Risk Score (1989)"]["auc_5y"] > 0.6
    assert by_name["HepatiQ v1 logistic regression (resubstitution)"]["auc_5y"] > 0.8
    for row in rows:
        assert 0.0 <= row["c_index"] <= 1.0


def test_udca_stored_score_benchmark_uses_complete_cases() -> None:
    row = benchmark_udca_stored_score(load_udca1(), n_boot=80)
    assert row["n_survival"] == 169
    assert 0.5 < row["auc_5y"] < 0.95


def test_derivation_validation_split_reproduces_dickson() -> None:
    split = benchmark_derivation_validation_split(load_pbc(), n_boot=50)
    assert split["derivation"]["n"] == 257
    assert split["derivation"]["events"] == 98
    assert split["validation"]["n"] == 72
    assert split["validation"]["events"] == 34
    assert split["validation"]["n_with_mrs"] == 70
    for row in split["scores"]:
        assert 0.7 < row["auc_5y"] < 0.95
