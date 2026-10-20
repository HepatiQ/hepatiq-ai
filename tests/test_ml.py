"""ml/ guards: leakage columns stay out, sex encoding matches training, selection rule is deterministic."""

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "ml"))

from impute_pipeline import ID_COL, LEAKY_COLS, TARGET_COL, build_feature_frame  # noqa: E402


def test_feature_frame_drops_leaky_and_id_columns():
    df = pd.read_csv(REPO_ROOT / "data" / "pbc_5yr_target.csv")
    features, ids, target = build_feature_frame(df)
    for col in [*LEAKY_COLS, ID_COL, TARGET_COL]:
        assert col not in features.columns
    assert len(features.columns) == 17
    assert len(ids) == len(df) and len(target) == len(df)


def test_sex_encoding_is_f_0_m_1():
    df = pd.read_csv(REPO_ROOT / "data" / "pbc_5yr_target.csv")
    features, _, _ = build_feature_frame(df)
    assert features["sex"].isna().sum() == 0
    assert set(features["sex"].unique()) == {0, 1}
    raw_sex = df["sex"].astype(str).str.lower()
    assert (features.loc[raw_sex == "f", "sex"] == 0).all()
    assert (features.loc[raw_sex == "m", "sex"] == 1).all()


def _roc_block(mean, lower):
    return {
        "roc_auc": {"mean": mean, "ci95_lower": lower, "std": 0.02},
        "brier_score": {"mean": 0.15},
        "recall": {"mean": 0.8, "std": 0.05},
        "precision": {"mean": 0.75},
    }


def test_select_winner_picks_top_when_cis_clearly_separated():
    sys.path.insert(0, str(REPO_ROOT / "ml"))
    from train import select_winner

    results = {"a": _roc_block(0.90, 0.85), "b": _roc_block(0.80, 0.70)}
    winner, reason = select_winner(results)
    assert winner == "a"
    assert "highest mean ROC-AUC" in reason


def test_select_winner_falls_back_to_calibration_on_overlapping_cis():
    sys.path.insert(0, str(REPO_ROOT / "ml"))
    from train import select_winner

    a = _roc_block(0.90, 0.80)
    a["brier_score"] = {"mean": 0.15}
    b = _roc_block(0.88, 0.82)
    b["brier_score"] = {"mean": 0.10}
    winner, reason = select_winner({"a": a, "b": b})
    assert winner == "b"
    assert "calibration" in reason
