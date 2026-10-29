"""POST /predict contract: schema, validation bounds, and joblib parity."""

import pytest

from hepatiq.backend.main import FEATURE_COLUMNS
from tests.conftest import OLD_5FEATURE, REQUIRED_ONLY, SAMPLE_FULL, build_model_frame


def test_required_5_returns_200(client):
    r = client.post("/predict", json=REQUIRED_ONLY)
    assert r.status_code == 200, r.text
    assert 0.0 <= r.json()["probability"] <= 1.0
    assert r.json()["model_loaded"] is True


def test_required_5_returns_17_contributions_with_12_imputed(client):
    contributions = client.post("/predict", json=REQUIRED_ONLY).json()["contributions"]
    assert len(contributions) == 17
    assert sum(c["imputed"] for c in contributions) == 12
    assert all(c["imputed"] == (c["value"] is None) for c in contributions)


def test_full_17_returns_200_with_all_impacts(client):
    r = client.post("/predict", json=SAMPLE_FULL)
    assert r.status_code == 200, r.text
    contributions = r.json()["contributions"]
    assert len(contributions) == 17
    assert all(c["impact"] is not None for c in contributions)
    assert all(c["imputed"] is False for c in contributions)
    assert any(c["feature"] == "alk.phos" for c in contributions)


def test_old_5_feature_payload_rejected(client):
    assert client.post("/predict", json=OLD_5FEATURE).status_code == 422


def test_platelet_in_raw_units_rejected(client):
    payload = dict(SAMPLE_FULL, platelet=200000.0)
    assert client.post("/predict", json=payload).status_code == 422


def test_unknown_field_rejected(client):
    payload = dict(REQUIRED_ONLY, bilirubin=1.0)
    assert client.post("/predict", json=payload).status_code == 422


@pytest.mark.parametrize("sex", ["f", "F", "m", "M"])
def test_sex_is_case_insensitive(client, sex):
    payload = dict(REQUIRED_ONLY, sex=sex)
    r = client.post("/predict", json=payload)
    assert r.status_code == 200, r.text


def test_probability_matches_sex_encoding(client, model):
    r_f = client.post("/predict", json=dict(REQUIRED_ONLY, sex="f"))
    r_m = client.post("/predict", json=dict(REQUIRED_ONLY, sex="m"))
    x = build_model_frame(REQUIRED_ONLY)
    direct_f = float(model.predict_proba(x)[0, 1])
    x["sex"] = 1.0
    direct_m = float(model.predict_proba(x)[0, 1])
    assert abs(r_f.json()["probability"] - direct_f) < 1e-9
    assert abs(r_m.json()["probability"] - direct_m) < 1e-9


@pytest.mark.parametrize(
    "field,value",
    [("age", -5), ("age", 130), ("bili", 1000), ("albumin", 50), ("stage", 7), ("protime", 0)],
)
def test_out_of_bounds_values_rejected(client, field, value):
    payload = dict(REQUIRED_ONLY, **{field: value})
    assert client.post("/predict", json=payload).status_code == 422


def test_full_payload_probability_matches_direct_joblib(client, model):
    r = client.post("/predict", json=SAMPLE_FULL)
    assert r.status_code == 200
    direct = float(model.predict_proba(build_model_frame(SAMPLE_FULL))[0, 1])
    assert abs(r.json()["probability"] - direct) < 1e-9


def test_required_5_probability_matches_direct_joblib(client, model):
    """Omitted optionals -> NaN -> IterativeImputer; API and joblib must agree exactly."""
    r = client.post("/predict", json=REQUIRED_ONLY)
    assert r.status_code == 200
    direct = float(model.predict_proba(build_model_frame(REQUIRED_ONLY))[0, 1])
    assert abs(r.json()["probability"] - direct) < 1e-9


def test_contributions_use_training_feature_names(client):
    contributions = client.post("/predict", json=SAMPLE_FULL).json()["contributions"]
    assert [c["feature"] for c in contributions] == FEATURE_COLUMNS


# docs/DEMO.md patients — verified probabilities: A ≈ 9.7%, B ≈ 27.5%, C ≈ 99.4%.
DEMO_PATIENT_A = {"age": 45.0, "sex": "f", "edema": 0.0, "bili": 0.6, "albumin": 4.0}
DEMO_PATIENT_B = {"age": 55.0, "sex": "f", "edema": 0.0, "bili": 1.0, "albumin": 3.5}
DEMO_PATIENT_C = {
    "age": 68.0, "sex": "m", "edema": 0.5, "bili": 8.0, "albumin": 2.9,
    "ascites": 1.0, "protime": 13.5, "platelet": 180.0,
}


@pytest.mark.parametrize(
    "payload,band",
    [(DEMO_PATIENT_A, "low"), (DEMO_PATIENT_B, "intermediate"), (DEMO_PATIENT_C, "high")],
)
def test_risk_band_matches_demo_patients(client, payload, band):
    r = client.post("/predict", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["risk_band"] == band


@pytest.mark.parametrize("payload", [REQUIRED_ONLY, SAMPLE_FULL])
def test_in_range_inputs_produce_no_warnings(client, payload):
    r = client.post("/predict", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["warnings"] == []


def test_out_of_training_range_yields_warning(client):
    # age 120 passes API bounds (le=120) but exceeds the training max (~76.7).
    r = client.post("/predict", json=dict(REQUIRED_ONLY, age=120.0))
    assert r.status_code == 200, r.text
    warnings = r.json()["warnings"]
    assert any(w.startswith("age=") for w in warnings)
    assert any("outside the training range" in w for w in warnings)
    assert any("extrapolating" in w for w in warnings)
