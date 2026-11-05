# ruff: noqa: E402
"""Run the frozen feature-ablation and imputation audit.

Examples:
    python scripts/research/run_audit.py smoke
    python scripts/research/run_audit.py ablation
    python scripts/research/run_audit.py imputation
    python scripts/research/run_audit.py heldout --confirm-heldout
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import numpy as np
import pandas as pd

from hepatiq.data.schema import validate_pbc
from hepatiq.paths import EXTERNAL_PBC
from hepatiq.research.ablation import (
    coefficient_stability,
    collinearity_diagnostics,
    compare_predictions,
    heldout_evaluation,
    learning_curve_summary,
    make_pipeline,
    optimism_correction_multi,
    run_feature_set_suite,
    run_oof,
    summarize_oof,
)
from hepatiq.research.censoring import bound_summary, death_only_summary
from hepatiq.research.config import (
    DECISION_THRESHOLDS,
    FEATURE_SETS,
    N_OPTIMISM_RESAMPLES,
    PRIMARY_SEED,
    REPEATED_SEEDS,
    REPORT_THRESHOLDS,
)
from hepatiq.research.data import load_research_cohort
from hepatiq.research.imputation import (
    all_patient_sensitivity,
    all_patient_shap_sensitivity,
    load_model,
    patient_b_audit,
    patient_b_shap_sensitivity,
)
from hepatiq.research.mayo import compare_discrimination
from hepatiq.research.metrics import (
    auc_score,
    brier_score,
    calibration_slope_intercept,
    classification_metrics,
    decision_curve,
)
from hepatiq.research.reporting import write_csv, write_json

DEFAULT_OUT = Path("docs/research/artifacts")


def _cohort():
    return load_research_cohort()


def smoke(out_dir: Path) -> dict:
    cohort = _cohort()
    model = load_model()
    f17 = summarize_oof(run_oof(cohort, FEATURE_SETS["F17"], seed=PRIMARY_SEED))
    f5 = summarize_oof(run_oof(cohort, FEATURE_SETS["F5"], seed=PRIMARY_SEED))
    patient = patient_b_audit(model, cohort.features)

    payload = {
        "cohort": {
            "n": cohort.n,
            "events": cohort.n_events,
            "nonevents": cohort.n - cohort.n_events,
            "features": list(cohort.features.columns),
        },
        "f17": f17,
        "f5": f5,
        "patient_b": patient,
    }
    write_json(out_dir / "smoke.json", payload)

    print(f"cohort n={cohort.n} events={cohort.n_events}")
    for label, summary in (("F17", f17), ("F5", f5)):
        print(
            f"{label}: AUC {summary['auc']['point']:.4f} "
            f"[{summary['auc']['lower']:.4f}, {summary['auc']['upper']:.4f}], "
            f"Brier {summary['brier']['point']:.4f}, slope {summary['calibration_slope']:.4f}"
        )
    print(
        "Patient B baseline: "
        f"{patient['baseline_prediction']:.4f} "
        f"(documented match={patient['baseline_matches_documented']})"
    )
    return payload


def ablation(out_dir: Path, seeds: tuple[int, ...]) -> dict:
    cohort = _cohort()
    suite = run_feature_set_suite(cohort, seeds=seeds)
    payload = {"protocol": "F17 vs F5 primary; all others secondary", "suite": suite}
    write_json(out_dir / "ablation.json", payload)

    rows = []
    for key, value in suite.items():
        summary = value["summary"]
        rows.append(
            {
                "comparison": key,
                "auc": summary["auc"]["point"],
                "auc_lower": summary["auc"]["lower"],
                "auc_upper": summary["auc"]["upper"],
                "brier": summary["brier"]["point"],
                "calibration_slope": summary["calibration_slope"],
                "calibration_intercept": summary["calibration_intercept"],
                "mean_predicted": summary["mean_predicted"],
                "observed": summary["observed"],
                "ece": summary["ece"],
                "ici": summary["ici"],
            }
        )
    write_csv(out_dir / "ablation_summary.csv", pd.DataFrame(rows))
    return payload


def primary(out_dir: Path, seeds: tuple[int, ...]) -> dict:
    cohort = _cohort()
    calibration: dict[str, dict] = {}
    comparisons: dict[str, dict] = {}
    repeated: dict[str, dict] = {}

    for weighted in (True, False):
        label = "weighted" if weighted else "unweighted"
        f17 = run_oof(cohort, FEATURE_SETS["F17"], weighted=weighted, seed=PRIMARY_SEED)
        f5 = run_oof(cohort, FEATURE_SETS["F5"], weighted=weighted, seed=PRIMARY_SEED)
        comparisons[label] = compare_predictions(
            f17["y_true"], f17["y_prob"], f5["y_prob"], n_boot=2000, seed=PRIMARY_SEED
        )

        for key, result in (("F17", f17), ("F5", f5)):
            summary = summarize_oof(result)
            summary["classification"] = {
                str(threshold): classification_metrics(
                    result["y_true"], result["y_prob"], threshold
                )
                for threshold in REPORT_THRESHOLDS
            }
            curve = decision_curve(result["y_true"], result["y_prob"], DECISION_THRESHOLDS)
            summary["decision_curve"] = {name: values.tolist() for name, values in curve.items()}
            calibration[f"{key}|{label}"] = summary

        rows = []
        for seed in seeds:
            seed_f17 = run_oof(cohort, FEATURE_SETS["F17"], weighted=weighted, seed=seed)
            seed_f5 = run_oof(cohort, FEATURE_SETS["F5"], weighted=weighted, seed=seed)
            rows.append(
                {
                    "seed": seed,
                    "delta_auc": auc_score(seed_f17["y_true"], seed_f17["y_prob"])
                    - auc_score(seed_f5["y_true"], seed_f5["y_prob"]),
                    "delta_calibration_slope": calibration_slope_intercept(
                        seed_f17["y_true"], seed_f17["y_prob"]
                    )[0]
                    - calibration_slope_intercept(seed_f5["y_true"], seed_f5["y_prob"])[0],
                }
            )
        aucs = np.asarray([row["delta_auc"] for row in rows], dtype=float)
        slopes = np.asarray([row["delta_calibration_slope"] for row in rows], dtype=float)
        repeated[label] = {
            "repeats": rows,
            "delta_auc": {
                "mean": float(aucs.mean()),
                "sd": float(aucs.std(ddof=1)),
                "min": float(aucs.min()),
                "max": float(aucs.max()),
                "positive_seeds": int((aucs > 0).sum()),
            },
            "delta_calibration_slope": {
                "mean": float(slopes.mean()),
                "sd": float(slopes.std(ddof=1)),
                "min": float(slopes.min()),
                "max": float(slopes.max()),
                "negative_seeds": int((slopes < 0).sum()),
            },
        }

    payload = {
        "calibration": calibration,
        "comparisons_F17_minus_F5": comparisons,
        "repeated_deltas": repeated,
    }
    write_json(out_dir / "calibration_primary.json", calibration)
    write_json(out_dir / "primary_comparisons.json", comparisons)
    write_json(out_dir / "repeated_primary_deltas.json", repeated)
    return payload


def diagnostics(out_dir: Path) -> dict:
    cohort = _cohort()
    payload = {
        "collinearity": collinearity_diagnostics(cohort),
        "coefficient_stability": coefficient_stability(cohort),
        "learning_curves": {
            key: learning_curve_summary(cohort, FEATURE_SETS[key]) for key in ("F5", "F17")
        },
    }
    write_json(out_dir / "diagnostics.json", payload)
    write_csv(out_dir / "coefficient_stability.csv", payload["coefficient_stability"])
    return payload


def imputation(out_dir: Path) -> dict:
    cohort = _cohort()
    model = load_model()
    payload = patient_b_audit(model, cohort.features)
    payload["note"] = "imputed values are synthetic; never treat them as measurements"

    f5_features = cohort.features[list(FEATURE_SETS["F5"])]
    f5_model = make_pipeline("lr", weighted=True, seed=PRIMARY_SEED)
    f5_model.fit(f5_features, cohort.target)
    f5_payload = patient_b_audit(f5_model, f5_features)
    f5_payload["note"] = "exploratory full-cohort F5 fit, not the deployed model"

    write_json(out_dir / "imputation_patient_b.json", payload)
    write_json(out_dir / "patient_b_f5_vs_f17.json", {"F17": payload, "F5": f5_payload})
    write_csv(out_dir / "imputation_scenarios.csv", pd.DataFrame(payload["scenarios"]))
    write_csv(out_dir / "imputation_tornado.csv", pd.DataFrame(payload["tornado"]))
    return payload


def _optimism_slope(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    return float(calibration_slope_intercept(y_true, y_prob)[0])


def _optimism_intercept(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    return float(calibration_slope_intercept(y_true, y_prob)[1])


def optimism(out_dir: Path) -> dict:
    cohort = _cohort()
    metrics = {
        "auc": auc_score,
        "brier": brier_score,
        "calibration_slope": _optimism_slope,
        "calibration_intercept": _optimism_intercept,
    }
    payload: dict[str, object] = {}
    for key in ("F5", "F17"):
        payload[key] = {}
        for weighted in (False, True):
            label = "weighted" if weighted else "unweighted"
            print(f"optimism: {key} {label} ({N_OPTIMISM_RESAMPLES} resamples)")
            payload[key][label] = optimism_correction_multi(
                cohort,
                FEATURE_SETS[key],
                metric_fns=metrics,
                weighted=weighted,
                n_resamples=N_OPTIMISM_RESAMPLES,
                seed=PRIMARY_SEED,
            )
    write_json(out_dir / "optimism.json", payload)
    return payload


def all_sensitivity(out_dir: Path) -> dict:
    cohort = _cohort()
    payload = all_patient_sensitivity(load_model(), cohort.frame, cohort.features)
    write_json(out_dir / "all_patient_sensitivity.json", payload)
    return payload


def attribution(out_dir: Path) -> dict:
    cohort = _cohort()
    model = load_model()
    payload = {
        "patient_b": patient_b_shap_sensitivity(model, cohort.features),
        "all_patients": all_patient_shap_sensitivity(model, cohort.features),
        "note": "SHAP values are log-odds; imputed inputs are synthetic and not measurements",
    }
    write_json(out_dir / "imputation_attribution.json", payload)
    return payload


def censoring(out_dir: Path) -> dict:
    frame = pd.read_csv(EXTERNAL_PBC)
    validate_pbc(frame)
    payload = {
        "bounds": bound_summary(frame),
        "death_only": death_only_summary(frame),
        "note": "best/worst-case bounds include censoring uncertainty; death-only drops transplants",
    }
    write_json(out_dir / "censoring_bounds.json", payload)
    return payload


def mayo(out_dir: Path) -> dict:
    cohort = _cohort()
    result = run_oof(cohort, FEATURE_SETS["F17"], weighted=True, seed=PRIMARY_SEED)
    payload = compare_discrimination(cohort.frame, result["y_prob"])
    payload["hepatiq_predictions"] = "out-of-fold F17 weighted, seed 42"
    write_json(out_dir / "mayo_discrimination.json", payload)
    return payload


def heldout(out_dir: Path, confirm: bool) -> dict:
    if not confirm:
        raise SystemExit("refusing to touch the 312/106 split without --confirm-heldout")
    if (out_dir / "heldout_once.json").exists():
        raise SystemExit("held-out already evaluated; refusing to overwrite heldout_once.json")
    cohort = _cohort()
    payload = {
        "F17": heldout_evaluation(cohort, FEATURE_SETS["F17"], weighted=True),
        "F5": heldout_evaluation(cohort, FEATURE_SETS["F5"], weighted=True),
        "note": "one-time internal 312/106 split; no model selection or threshold tuning",
    }
    write_json(out_dir / "heldout_once.json", payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "smoke",
            "primary",
            "diagnostics",
            "ablation",
            "imputation",
            "all-sensitivity",
            "attribution",
            "optimism",
            "censoring",
            "mayo",
            "heldout",
            "all",
        ),
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seeds", type=int, nargs="*", default=None)
    parser.add_argument("--confirm-heldout", action="store_true")
    args = parser.parse_args(argv)
    seeds = tuple(args.seeds) if args.seeds else REPEATED_SEEDS

    args.out_dir.mkdir(parents=True, exist_ok=True)
    try:
        if args.command == "smoke":
            smoke(args.out_dir)
        elif args.command == "primary":
            primary(args.out_dir, seeds)
        elif args.command == "diagnostics":
            diagnostics(args.out_dir)
        elif args.command == "ablation":
            ablation(args.out_dir, seeds)
        elif args.command == "imputation":
            imputation(args.out_dir)
        elif args.command == "all-sensitivity":
            all_sensitivity(args.out_dir)
        elif args.command == "attribution":
            attribution(args.out_dir)
        elif args.command == "optimism":
            optimism(args.out_dir)
        elif args.command == "censoring":
            censoring(args.out_dir)
        elif args.command == "mayo":
            mayo(args.out_dir)
        elif args.command == "heldout":
            heldout(args.out_dir, args.confirm_heldout)
        else:
            primary(args.out_dir, seeds)
            diagnostics(args.out_dir)
            ablation(args.out_dir, seeds)
            imputation(args.out_dir)
            all_sensitivity(args.out_dir)
            attribution(args.out_dir)
            optimism(args.out_dir)
            censoring(args.out_dir)
            mayo(args.out_dir)
            if args.confirm_heldout:
                heldout(args.out_dir, True)
            else:
                print("held-out split not touched (pass --confirm-heldout to run it once)")
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
