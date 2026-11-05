"""Patient-level imputation sensitivity and determinism."""

import numpy as np
import pytest

from hepatiq.research.ablation import make_pipeline
from hepatiq.research.config import (
    ALL_FEATURES,
    FEATURE_SETS,
    IMPUTED_OPTIONAL_FEATURES,
    PATIENT_B,
    PATIENT_B_EXPECTED,
)
from hepatiq.research.data import load_research_cohort
from hepatiq.research.imputation import (
    all_patient_sensitivity,
    all_patient_shap_sensitivity,
    encode_patient,
    imputed_values,
    load_model,
    multiple_imputation_predictions,
    patient_b_scenarios,
    patient_b_sensitivity,
    patient_b_shap_sensitivity,
    predict_patient,
    risk_band,
    tornado,
)

PAYLOAD = dict(PATIENT_B)


@pytest.fixture(scope="module")
def cohort():
    return load_research_cohort()


@pytest.fixture(scope="module")
def model():
    return load_model()


def test_patient_b_reproduces_documented_prediction(model):
    assert predict_patient(model, PAYLOAD) == pytest.approx(PATIENT_B_EXPECTED, abs=1e-12)


def test_optional_fields_stay_missing_until_imputation():
    row = encode_patient(PAYLOAD, ALL_FEATURES)
    assert row.shape == (1, len(ALL_FEATURES))
    assert np.isnan(row["trt"].iloc[0])
    assert np.isnan(row["stage"].iloc[0])
    assert row["sex"].iloc[0] == 0.0


def test_required_fields_and_sex_are_validated():
    with pytest.raises(ValueError, match="required"):
        encode_patient({"sex": "f", "edema": 0, "bili": 1.0, "albumin": 3.5}, ALL_FEATURES)
    with pytest.raises(ValueError, match="sex"):
        encode_patient({"age": 55, "edema": 0, "bili": 1.0, "albumin": 3.5}, ALL_FEATURES)
    with pytest.raises(ValueError, match="sex"):
        encode_patient({**PAYLOAD, "sex": "x"}, ALL_FEATURES)


def test_imputer_fills_the_expected_optional_features(model):
    values = imputed_values(model, PAYLOAD)
    assert values.index.tolist() == list(ALL_FEATURES)
    assert values.notna().all()
    assert values["stage"] > 0
    assert values["copper"] > 0


def test_patient_b_scenarios_and_tornado_are_complete(cohort, model):
    scenarios = patient_b_sensitivity(model, cohort.features)
    assert "only_observed" in set(scenarios["scenario"])
    assert len(scenarios) == 11
    assert scenarios.loc[scenarios["scenario"] == "only_observed", "delta_pp"].iloc[0] == pytest.approx(0.0)

    table = tornado(model, cohort.features)
    assert set(table["feature"]) == set(IMPUTED_OPTIONAL_FEATURES)
    assert len(table) == len(IMPUTED_OPTIONAL_FEATURES) * 5


def test_optional_scenarios_keep_observed_fields_fixed(cohort):
    scenarios = patient_b_scenarios(cohort.features)
    for name in ("cohort_typical", "clinically_normal", "p10_optional", "p50_optional", "p90_optional"):
        for field in ("age", "bili", "albumin", "edema", "sex"):
            assert scenarios[name][field] == PAYLOAD[field]


def test_five_feature_model_tornado_uses_only_its_own_inputs(cohort):
    features = cohort.features[list(FEATURE_SETS["F5"])]
    pipeline = make_pipeline("lr", weighted=True)
    pipeline.fit(features, cohort.target)
    table = tornado(pipeline, features)
    assert set(table["feature"]) == {"protime"}
    assert len(table) == 5


def test_multiple_imputation_is_deterministic(cohort, model):
    first = multiple_imputation_predictions(model, PAYLOAD, cohort.features, n_imputations=3, seed=11)
    second = multiple_imputation_predictions(model, PAYLOAD, cohort.features, n_imputations=3, seed=11)
    assert first.shape == (3,)
    assert np.isfinite(first).all()
    assert np.allclose(first, second)


def test_risk_band_boundaries():
    assert risk_band(0.0) == "low"
    assert risk_band(0.149) == "low"
    assert risk_band(0.15) == "moderate"
    assert risk_band(0.399) == "moderate"
    assert risk_band(0.40) == "high"
    assert risk_band(1.0) == "high"


def test_all_patient_sensitivity_covers_the_full_cohort(cohort, model):
    result = all_patient_sensitivity(
        model, cohort.frame, cohort.features, n_imputations=2
    )
    assert result["n"] == cohort.n
    assert sum(result["baseline_bands"].values()) == cohort.n
    assert sum(result["mean_mi_bands"].values()) == cohort.n
    assert result["randomized"]["n"] + result["non_randomized"]["n"] == cohort.n
    assert 0 <= result["mean_band_change_rate"] <= 1
    assert 0 <= result["any_draw_band_change_rate"] <= 1
    assert result["mean_scenario_range_pp"] >= 0


def test_patient_b_shap_attribution_tracks_scenarios(cohort, model):
    result = patient_b_shap_sensitivity(model, cohort.features)
    assert result["baseline"]["top_feature"] in ALL_FEATURES
    assert len(result["baseline"]["contributions"]) == len(ALL_FEATURES)
    assert len(result["scenarios"]) == 11
    by_name = {row["scenario"]: row for row in result["scenarios"]}
    assert by_name["only_observed"]["mean_abs_change_log_odds"] == pytest.approx(0.0)
    assert by_name["clinically_normal"]["mean_abs_change_log_odds"] > 0
    assert by_name["p90_optional"]["top_feature"] in ALL_FEATURES


def test_all_patient_shap_summary_covers_the_cohort(cohort, model):
    result = all_patient_shap_sensitivity(model, cohort.features, n_imputations=1)
    assert result["n"] == cohort.n
    assert set(result["scenarios"]) == {
        "only_observed",
        "cohort_typical",
        "clinically_normal",
        "p10_optional",
        "p90_optional",
    }
    for summary in result["scenarios"].values():
        assert 0 <= summary["top_feature_change_rate"] <= 1
        assert summary["mean_abs_change_log_odds"] >= 0
    assert result["multiple_imputation"]["n_draws"] == 1
    assert 0 <= result["multiple_imputation"]["draw_top_feature_change_rate"] <= 1
    assert set(result["multiple_imputation"]["mean_abs_change_by_feature"]) == set(ALL_FEATURES)
