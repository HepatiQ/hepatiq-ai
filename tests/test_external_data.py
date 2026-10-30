"""Contract and integrity tests for the canonical external PBC datasets."""

from __future__ import annotations

import json

import pytest

from hepatiq import paths
from hepatiq.data import (
    DataIntegrityError,
    dataset_summary,
    load_all,
    load_pbc,
    load_pbcseq,
    load_udca,
    load_udca1,
    load_udca2,
    schema,
    verify_datasets,
)


def test_provenance_hashes_match_pinned_files():
    datasets = verify_datasets()
    assert set(datasets) == {"pbc", "pbcseq", "udca", "udca1", "udca2"}
    assert dataset_summary()["pbc"]["rows"] == 418


def test_pbc_contract_and_derived_flags():
    frame = load_pbc()
    assert frame.shape[0] == 418
    assert frame["id"].is_unique
    assert 419 not in set(frame["id"]), "canonical pbc must not include the demo row"
    assert set(frame["status"]).issubset({0, 1, 2})
    assert frame["trt"].notna().sum() == schema.RANDOMIZED_PATIENTS
    assert set(frame["trt"].dropna()) == {1, 2}
    assert int(frame["event"].sum()) == int(frame["death"].sum()) + int(frame["transplant"].sum())
    assert frame["trt_label"].dropna().isin(["D-penicillamine", "placebo"]).all()


def test_pbcseq_is_longitudinal_subset_of_pbc():
    pbc = load_pbc()
    seq = load_pbcseq()
    assert seq.shape[0] == 1945
    assert seq["id"].nunique() == schema.RANDOMIZED_PATIENTS
    assert set(seq["id"]).issubset(set(pbc["id"]))
    assert (seq["day"] >= 0).all()
    assert (seq["day"] <= seq["futime"]).all()
    assert seq.groupby("id")["day"].min().eq(0).all()


def test_landmark_cohort_shrinks_to_patients_with_a_12_month_visit():
    """Only 254/312 patients have a visit at/after day 365; Model B must use them."""
    seq = load_pbcseq()
    max_day = seq.groupby("id")["day"].max()
    eligible = max_day[max_day >= 365].index
    assert len(eligible) == 254
    assert len(eligible) < schema.RANDOMIZED_PATIENTS
    pbc = load_pbc().set_index("id")
    assert (pbc.loc[eligible, "time"] > 365).all()


def test_udca_stored_score_and_zero_followup_row():
    udca = load_udca()
    assert udca.shape[0] == 170
    assert udca["riskscore"].isna().sum() == 1
    assert udca.loc[udca["riskscore"].isna(), "id"].tolist() == [151]

    udca1 = load_udca1()
    assert udca1.shape[0] == 170
    zero = udca1.loc[udca1["futime"] == 0, "id"].tolist()
    assert tuple(zero) == schema.UDCA_ZERO_FOLLOWUP_IDS
    assert udca1.loc[udca1["futime"] == 0, "status"].eq(0).all()
    assert load_udca2().shape[0] == 1360


def test_load_all_checks_alignment():
    tables = load_all()
    assert set(tables) == {"pbc", "pbcseq", "udca", "udca1", "udca2"}


def test_integrity_check_fails_on_edited_hash(tmp_path):
    provenance = json.loads(paths.EXTERNAL_PROVENANCE.read_text(encoding="utf-8"))
    provenance["datasets"]["pbc"]["sha256"] = "0" * 64
    tampered = tmp_path / "PROVENANCE.json"
    tampered.write_text(json.dumps(provenance), encoding="utf-8")

    with pytest.raises(DataIntegrityError, match="does not match pinned"):
        verify_datasets(provenance_path=tampered)


def test_integrity_check_fails_on_missing_file(tmp_path):
    with pytest.raises(DataIntegrityError, match="missing"):
        verify_datasets(base_dir=tmp_path)


def test_loader_error_names_regeneration_command(tmp_path):
    with pytest.raises(DataIntegrityError, match="export_r_datasets.py"):
        load_pbc(path=tmp_path / "absent.csv")
