"""Out-of-fold harness determinism and missing-indicator pipeline."""

import numpy as np
import pytest

from hepatiq.research.ablation import collinearity_diagnostics, optimism_correction_multi, run_oof
from hepatiq.research.config import FEATURE_SETS, PRIMARY_SEED
from hepatiq.research.data import load_research_cohort
from hepatiq.research.metrics import auc_score, brier_score


def test_oof_is_deterministic_and_visits_every_fold():
    cohort = load_research_cohort()
    first = run_oof(cohort, FEATURE_SETS["F5"], seed=PRIMARY_SEED)
    second = run_oof(cohort, FEATURE_SETS["F5"], seed=PRIMARY_SEED)

    assert len(first["y_prob"]) == cohort.n
    assert np.isfinite(first["y_prob"]).all()
    assert set(np.unique(first["fold"])) == set(range(5))
    assert np.allclose(first["y_prob"], second["y_prob"])


def test_missing_indicator_pipeline_runs_end_to_end():
    cohort = load_research_cohort()
    result = run_oof(
        cohort,
        FEATURE_SETS["F17+IND"],
        add_indicators=True,
        seed=PRIMARY_SEED,
    )
    assert len(result["y_prob"]) == cohort.n
    assert np.isfinite(result["y_prob"]).all()
    assert np.all((result["y_prob"] >= 0) & (result["y_prob"] <= 1))


def test_collinearity_diagnostics_cover_every_feature():
    cohort = load_research_cohort()
    result = collinearity_diagnostics(cohort)
    assert result["condition_number"] > 1
    assert set(result["vif"]) == set(FEATURE_SETS["F17"])
    assert all(value >= 1 for value in result["vif"].values())


def test_optimism_correction_multi_reports_all_metrics():
    cohort = load_research_cohort()
    result = optimism_correction_multi(
        cohort,
        FEATURE_SETS["F5"],
        metric_fns={"auc": auc_score, "brier": brier_score},
        weighted=False,
        n_resamples=3,
    )
    assert set(result) == {"auc", "brier"}
    for metrics in result.values():
        assert metrics["n_resamples"] == 3
        assert metrics["optimism_corrected"] == pytest.approx(
            metrics["apparent"] - metrics["mean_optimism"]
        )
