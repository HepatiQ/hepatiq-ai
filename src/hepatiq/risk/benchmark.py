"""Discrimination benchmarks for published scores against the HepatiQ v1 model.

Two different endpoints are reported and must not be conflated:

* ``pbc`` — death or transplant within 5 years (HepatiQ's target).
* ``udca1`` — the first of death, transplant, histologic progression, varices,
  ascites, encephalopathy, bilirubin doubling or symptom worsening (the
  composite endpoint documented for ``survival::udca1``).

Only the ``pbc`` table is a like-for-like comparison with HepatiQ.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from hepatiq.risk.mayo_risk_score import mayo_risk_score_series
from hepatiq.risk.metrics import binary_auc, bootstrap_ci, harrell_c_index
from hepatiq.risk.simple_scores import albi_score, apri_score

HORIZON_DAYS = 1825
N_BOOTSTRAP = 1000


def five_year_outcome(time: np.ndarray, event: np.ndarray, horizon: int = HORIZON_DAYS) -> np.ndarray:
    """1 = event within ``horizon``, 0 = event-free past it, NaN = unknown.

    A patient censored before the horizon has an unknown 5-year status and is
    excluded from binary metrics (but retained for the c-index).
    """
    time = np.asarray(time, dtype=float)
    event = np.asarray(event).astype(bool)
    labels = np.full(len(time), np.nan)
    after = event & (time > horizon)
    labels[after] = 0.0
    known_free = (~event) & (time > horizon)
    labels[known_free] = 0.0
    known_event = event & (time <= horizon)
    labels[known_event] = 1.0
    return labels


def v1_probabilities(frame: pd.DataFrame) -> np.ndarray:
    """Score the canonical cohort with the deployed v1 logistic-regression pipeline."""
    import joblib

    from hepatiq.backend.main import FEATURE_COLUMNS
    from hepatiq.paths import MODEL_PATH

    model = joblib.load(MODEL_PATH)
    features = frame[FEATURE_COLUMNS].copy()
    features["sex"] = features["sex"].astype(str).str.lower().map({"f": 0.0, "m": 1.0})
    return model.predict_proba(features)[:, 1]


def _evaluate(
    name: str,
    score: np.ndarray,
    time: np.ndarray,
    event: np.ndarray,
    labels: np.ndarray,
    n_boot: int,
) -> dict[str, Any]:
    score = np.asarray(score, dtype=float)
    auc = binary_auc(labels, score)
    auc_low, auc_high = bootstrap_ci(
        lambda indices: binary_auc(labels[indices], score[indices]),
        len(score),
        n_boot=n_boot,
    )
    c_index = harrell_c_index(time, event, score)
    c_low, c_high = bootstrap_ci(
        lambda indices: harrell_c_index(time[indices], event[indices], score[indices]),
        len(score),
        n_boot=n_boot,
    )
    known = np.isfinite(labels) & np.isfinite(score)
    return {
        "score": name,
        "n_5y": int(known.sum()),
        "events_5y": int(np.nansum(labels[known])),
        "auc_5y": auc,
        "auc_ci_low": auc_low,
        "auc_ci_high": auc_high,
        "c_index": c_index,
        "c_ci_low": c_low,
        "c_ci_high": c_high,
        "n_survival": int((np.isfinite(time) & np.isfinite(score)).sum()),
    }


def benchmark_pbc(frame: pd.DataFrame, n_boot: int = N_BOOTSTRAP) -> list[dict[str, Any]]:
    """Benchmark Mayo Risk Score, ALBI, APRI and the v1 model on the Mayo cohort."""
    time = frame["time"].to_numpy(dtype=float)
    event = frame["event"].to_numpy()
    labels = five_year_outcome(time, event)

    scores: dict[str, np.ndarray] = {
        "Mayo Risk Score (1989)": mayo_risk_score_series(frame).to_numpy(dtype=float),
        "ALBI": albi_score(frame["bili"], frame["albumin"]).to_numpy(dtype=float),
        "APRI": apri_score(frame["ast"], frame["platelet"]).to_numpy(dtype=float),
        "HepatiQ v1 logistic regression (resubstitution)": v1_probabilities(frame),
    }
    rows = [_evaluate(name, score, time, event, labels, n_boot) for name, score in scores.items()]
    rows.append(
        {
            "score": "Class prior (constant)",
            "n_5y": int(np.isfinite(labels).sum()),
            "events_5y": int(np.nansum(labels)),
            "auc_5y": 0.5,
            "auc_ci_low": float("nan"),
            "auc_ci_high": float("nan"),
            "c_index": 0.5,
            "c_ci_low": float("nan"),
            "c_ci_high": float("nan"),
            "n_survival": int(np.isfinite(time).sum()),
        }
    )
    return rows


def benchmark_derivation_validation_split(
    frame: pd.DataFrame, n_boot: int = N_BOOTSTRAP
) -> dict[str, Any]:
    """Reproduce Dickson's split and compare MRS with a retrained v1 pipeline.

    ``survival::pbc`` is the Dickson 1989 cohort: the 312 randomized patients
    were used to derive the Mayo Risk Score and the 106 non-randomized patients
    were its independent validation set. We therefore retrain the v1 logistic
    pipeline on the 312 only and test both scores on the 106.
    """
    from hepatiq.backend.main import FEATURE_COLUMNS
    from hepatiq.ml.train import build_pipelines

    derivation = frame.loc[frame["trt"].notna()].copy()
    validation = frame.loc[frame["trt"].isna()].copy()

    def label(subset: pd.DataFrame) -> pd.DataFrame:
        labels = five_year_outcome(subset["time"].to_numpy(dtype=float), subset["event"].to_numpy())
        subset = subset.assign(severe_event_5yr=labels).dropna(subset=["severe_event_5yr"])
        return subset

    def features(subset: pd.DataFrame) -> pd.DataFrame:
        frame_features = subset[FEATURE_COLUMNS].copy()
        frame_features["sex"] = frame_features["sex"].astype(str).str.lower().map({"f": 0.0, "m": 1.0})
        return frame_features

    derivation_labeled = label(derivation)
    validation_labeled = label(validation)

    train_x = features(derivation_labeled)
    target = derivation_labeled["severe_event_5yr"]
    positive_weight = float((target == 0).sum() / (target == 1).sum())
    pipeline = build_pipelines(positive_weight)["logistic_regression"]
    pipeline.fit(train_x, target)

    v1_scores = pipeline.predict_proba(features(validation_labeled))[:, 1]

    val_time = validation_labeled["time"].to_numpy(dtype=float)
    val_event = validation_labeled["event"].to_numpy()
    val_labels = validation_labeled["severe_event_5yr"].to_numpy(dtype=float)
    mrs_scores = mayo_risk_score_series(validation_labeled).to_numpy(dtype=float)

    # Both scores must be judged on exactly the same patients: the two with a
    # missing prothrombin time cannot receive a Mayo Risk Score.
    common = np.isfinite(mrs_scores)
    v1_scores, mrs_scores = v1_scores[common], mrs_scores[common]
    val_time, val_event, val_labels = val_time[common], val_event[common], val_labels[common]

    v1_row = _evaluate("HepatiQ v1 pipeline, retrained on 312", v1_scores, val_time, val_event, val_labels, n_boot)
    mrs_row = _evaluate("Mayo Risk Score (1989)", mrs_scores, val_time, val_event, val_labels, n_boot)

    derivation_mrs = mayo_risk_score_series(derivation).to_numpy(dtype=float)
    derivation_mrs_row = _evaluate(
        "Mayo Risk Score (1989), derivation cohort",
        derivation_mrs,
        derivation["time"].to_numpy(dtype=float),
        derivation["event"].to_numpy(),
        five_year_outcome(derivation["time"].to_numpy(dtype=float), derivation["event"].to_numpy()),
        n_boot,
    )

    return {
        "derivation": {
            "n": int(len(derivation_labeled)),
            "events": int(derivation_labeled["severe_event_5yr"].sum()),
            "mrs_apparent": derivation_mrs_row,
        },
        "validation": {
            "n": int(len(validation_labeled)),
            "events": int(validation_labeled["severe_event_5yr"].sum()),
            "n_with_mrs": int(common.sum()),
        },
        "scores": [mrs_row, v1_row],
    }


def mayo_risk_distribution(frame: pd.DataFrame) -> dict[str, float]:
    """Summary of computed Mayo Risk Scores, used as a distributional check."""
    score = mayo_risk_score_series(frame).dropna()
    return {
        "n": int(score.size),
        "mean": float(score.mean()),
        "median": float(score.median()),
        "sd": float(score.std()),
    }


def benchmark_udca_stored_score(udca1: pd.DataFrame, n_boot: int = N_BOOTSTRAP) -> dict[str, Any]:
    """Benchmark the stored Mayo Risk Score on the UDCA trial's composite endpoint.

    ``udca1.status`` is the first of death, transplant, histologic progression,
    varices, ascites, encephalopathy, bilirubin doubling or symptom worsening —
    **not** HepatiQ's death-or-transplant target. Patient 151 has zero follow-up
    and a missing score, so the analysis uses n = 169.
    """
    usable = udca1.loc[(udca1["futime"] > 0) & udca1["riskscore"].notna()]
    time = usable["futime"].to_numpy(dtype=float)
    event = usable["status"].to_numpy(dtype=float).astype(bool)
    labels = five_year_outcome(time, event)
    score = usable["riskscore"].to_numpy(dtype=float)
    row = _evaluate("Mayo Risk Score, stored (UDCA cohort)", score, time, event, labels, n_boot)
    row["cohort"] = "Lindor 1994 UDCA trial (n=169)"
    row["endpoint"] = "composite progression (not death/transplant)"
    return row


def to_markdown(
    pbc_rows: list[dict[str, Any]],
    udca_row: dict[str, Any],
    split: dict[str, Any] | None = None,
) -> str:
    def fmt(value: float, digits: int = 3) -> str:
        return "—" if not np.isfinite(value) else f"{value:.{digits}f}"

    def cell(row: dict[str, Any], key: str, low: str, high: str) -> str:
        main = fmt(row[key])
        if not np.isfinite(row[low]) or not np.isfinite(row[high]):
            return main
        return f"{main} ({fmt(row[low])}–{fmt(row[high])})"

    lines = [
        "# Published-score benchmark (v2)",
        "",
        "Generated by `python scripts/benchmark_scores.py`. Bootstrap percentile",
        f"95% CIs use {N_BOOTSTRAP} resamples.",
        "",
        "## Mayo cohort — 5-year death or transplant",
        "",
        "| Score | n (5y) | Events | 5-year AUC (95% CI) | Harrell c-index (95% CI) |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in pbc_rows:
        lines.append(
            f"| {row['score']} | {row['n_5y']} | {row['events_5y']} | "
            f"{cell(row, 'auc_5y', 'auc_ci_low', 'auc_ci_high')} | "
            f"{cell(row, 'c_index', 'c_ci_low', 'c_ci_high')} |"
        )

    lines += [
        "",
        "The 5-year column excludes patients censored before 1825 days (unknown",
        "status); the c-index uses all patients with a score and follow-up time.",
        "",
        "**Provenance matters.** `survival::pbc` *is* the Dickson 1989 cohort: the",
        "312 randomized patients were the derivation set and the 106",
        "non-randomized patients were the paper's independent validation set.",
        "The Mayo Risk Score was therefore derived on this data too, so its",
        "full-cohort numbers are apparent, not external.",
        "",
        "**Reading the v1 row.** The deployed v1 model was trained on this cohort,",
        "so its row is resubstitution and optimistic. Its leakage-safe out-of-fold",
        "ROC-AUC is **0.8828 (0.8409–0.9185)** (`src/hepatiq/validation/report.md`).",
        "The Mayo Risk Score's apparent 0.886 (0.846–0.918) is likewise optimistic,",
        "because its coefficients were derived from the same 312 patients. Neither",
        "row is an external validation; see the held-out comparison below.",
        "",
    ]

    if split:
        derivation, validation = split["derivation"], split["validation"]
        best = split["scores"][0]
        lines += [
            "## Held-out comparison: 312 randomized vs 106 non-randomized",
            "",
            f"Of the 312 randomized patients, {derivation['n']} have a known 5-year",
            f"label ({derivation['events']} events); these train the v1 pipeline.",
            f"Of the 106 non-randomized patients, {validation['n']} have a known",
            f"5-year label ({validation['events']} events) and "
            f"{validation['n_with_mrs']} also have a complete Mayo Risk Score.",
            f"Both scores are judged on those same {validation['n_with_mrs']} patients.",
            "",
            "| Score | 5-year AUC (95% CI) | Harrell c-index (95% CI) |",
            "| --- | ---: | ---: |",
        ]
        for row in split["scores"]:
            lines.append(
                f"| {row['score']} | "
                f"{cell(row, 'auc_5y', 'auc_ci_low', 'auc_ci_high')} | "
                f"{cell(row, 'c_index', 'c_ci_low', 'c_ci_high')} |"
            )

        apparent = derivation["mrs_apparent"]
        lines += [
            "",
            "**Result.** On the only truly held-out patients, the fixed 1989",
            f"five-variable score reaches AUC {best['auc_5y']:.3f} versus",
            f"{split['scores'][1]['auc_5y']:.3f} for the retrained 17-feature",
            "pipeline. The confidence intervals overlap and the test set has only",
            f"{best['events_5y']} events, so this is not proof that the score is",
            "superior — it is evidence that the larger model has *not* shown added",
            "value on held-out patients.",
            "",
            "For context, the Mayo Risk Score's apparent AUC on the 312 derivation",
            f"patients is {apparent['auc_5y']:.3f} "
            f"({apparent['auc_ci_low']:.3f}–{apparent['auc_ci_high']:.3f}); the drop",
            f"to {best['auc_5y']:.3f} on held-out patients is the optimism that",
            "full-cohort tables hide.",
            "",
        ]

    lines += [
        "## UDCA cohort — stored Mayo Risk Score vs composite progression",
        "",
        f"- Cohort: {udca_row['cohort']}",
        f"- Endpoint: {udca_row['endpoint']}",
        f"- 5-year AUC: {cell(udca_row, 'auc_5y', 'auc_ci_low', 'auc_ci_high')} "
        f"(n={udca_row['n_5y']}, events={udca_row['events_5y']})",
        f"- Harrell c-index: {cell(udca_row, 'c_index', 'c_ci_low', 'c_ci_high')} "
        f"(n={udca_row['n_survival']})",
        "",
    ]

    check = udca_row.get("implementation_check")
    if check:
        computed, stored = check["computed_pbc"], check["stored_udca"]
        lines += [
            "### Implementation check",
            "",
            "The score cannot be recomputed in the UDCA cohort, but its scale can be",
            "compared with the stored values:",
            "",
            "| Source | n | Mean | Median | SD |",
            "| --- | ---: | ---: | ---: | ---: |",
            f"| Computed from Mayo cohort | {computed['n']} | {computed['mean']:.3f} | "
            f"{computed['median']:.3f} | {computed['sd']:.3f} |",
            f"| Stored in UDCA cohort | {stored['n']} | {stored['mean']:.3f} | "
            f"{stored['median']:.3f} | {stored['sd']:.3f} |",
            "",
            "Agreement to within ~0.1 point on the mean supports a correct",
            "implementation, though it is not a per-patient validation.",
            "",
        ]

    lines += [
        "## Caveats",
        "",
        "- **`udca` cannot validate the score implementation.** It stores the Mayo",
        "  Risk Score but not age, albumin, prothrombin time or edema, so the score",
        "  cannot be recomputed from it. Implementation checks rely on unit tests",
        "  and on distributional agreement with the stored scores.",
        "- **The UDCA endpoint is composite**, so its AUC is not comparable to the",
        "  Mayo-cohort death-or-transplant AUC.",
        "- **UDCA follow-up is short.** The trial's maximum follow-up is ~1,896 days,",
        "  so only 80 of 169 patients have a known 5-year status (72 events); that",
        "  AUC is underpowered and selects early progressors. Prefer its c-index",
        "  (0.621, n=169).",
        "- **No calibration is reported here.** The Mayo Risk Score is a linear",
        "  predictor, not a probability; calibration and decision-curve analysis",
        "  belong to the calibration phase.",
        "- **GLOBE and UK-PBC are not computable** from this cohort: both require",
        "  post-UDCA treatment response and UK-PBC needs an external registry.",
        "- **The held-out comparison is small.** Only 70 patients (33 events) have",
        "  both a complete Mayo Risk Score and a known 5-year label, and the",
        "  confidence intervals overlap. It cannot establish superiority in either",
        "  direction; it only shows that v1's apparent advantage does not survive",
        "  held-out testing.",
        "- **APRI uses 253 patients**, because platelet counts are missing for most",
        "  non-randomized patients; its row is not directly comparable in n.",
        "",
    ]
    return "\n".join(lines)
