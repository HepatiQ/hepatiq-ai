"""Train and compare three classifiers for 5-year severe-event risk in PBC patients.

Models compared: Logistic Regression, Random Forest, and XGBoost. All three
are shallow / regularized on purpose -- with a 329-patient cohort after the
censoring filter, an unconstrained model (deep trees, many boosting rounds,
no penalty) will fit noise in the training folds rather than signal.

Why imputation + scaling live INSIDE the pipeline, not as a separate
preprocessing step run once upfront (contrast with impute_pipeline.py, which
still exists as a standalone artifact for exploration/reporting, not as
train.py's input):
    If you fit IterativeImputer/StandardScaler on the full 329 patients once
    and then cross-validate on that already-transformed data, every fold's
    "held-out" patients were already seen by the imputer/scaler during that
    upfront fit. That's a leakage channel -- a small one, but a real one --
    and it can inflate the very confidence intervals we're relying on to
    trust the CV scores on a dataset this small. Wrapping both steps inside
    an sklearn Pipeline means each of the 5 folds fits its own imputer and
    scaler on ONLY that fold's training patients, and applies them to the
    held-out fold. Slower, but leakage-free.

Metrics: ROC-AUC, Precision, Recall, F1, and Brier score (calibration),
each reported as fold scores + mean + 95% CI across the 5 stratified folds.
The CI uses a t-distribution (df=4) since n=5 is too small for a normal
approximation to be trustworthy.

Model selection: models are first compared by mean ROC-AUC.
If ROC-AUC confidence intervals overlap, calibration (Brier score),
recall, precision, and recall stability are used as documented
tie-breakers. The selected model is then refit on the full cohort and
saved as models/model.pkl.

Run:
    python ml/train.py

Input:  data/pbc_5yr_target.csv   (labeled cohort, NOT yet imputed -- this
                                    is deliberate, see above)
Output: models/model.pkl           (winning pipeline, fit on full cohort)
        models/lr_model.pkl
        models/rf_model.pkl
        models/xgb_model.pkl
        models/training_metrics.json
"""

import os
import json

import numpy as np
import pandas as pd
from scipy import stats
import joblib

from sklearn.experimental import enable_iterative_imputer  # noqa: F401 (required to unlock IterativeImputer)
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate

try:
    from xgboost import XGBClassifier
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "xgboost is required for train.py but is not installed. "
        "Run `pip install xgboost` and add it to requirements.txt."
    ) from exc

# impute_pipeline.py lives next to this file (both under ml/); reusing its
# feature-encoding logic instead of re-deriving it keeps the two scripts
# from silently drifting apart on how "sex" gets encoded, which columns
# count as leaky, etc.
from impute_pipeline import build_feature_frame

INPUT_PATH = os.path.join("data", "pbc_5yr_target.csv")
MODELS_DIR = "models"
METRICS_PATH = os.path.join(MODELS_DIR, "training_metrics.json")

N_FOLDS = 5
RANDOM_STATE = 42

SHORT_NAMES = {
    "logistic_regression": "lr",
    "random_forest": "rf",
    "xgboost": "xgb",
}

SCORING = {
    "roc_auc": "roc_auc",
    "precision": "precision",
    "recall": "recall",
    "f1": "f1",
    "neg_brier_score": "neg_brier_score",
}


def build_pipelines(scale_pos_weight: float) -> dict:
    """Return {model_name: sklearn Pipeline}.

    Every pipeline imputes and scales internally (see module docstring for
    why), so each one can be handed straight to cross_validate as a single
    unit and later refit whole on the full cohort.
    """
    return {
        "logistic_regression": Pipeline([
            ("imputer", IterativeImputer(random_state=RANDOM_STATE, max_iter=10)),
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(
                # penalty defaults to "l2" in this sklearn version; leaving it
                # implicit avoids a FutureWarning without changing behavior
                C=1.0,
                class_weight="balanced",
                max_iter=2000,
                solver="lbfgs",
                random_state=RANDOM_STATE,
            )),
        ]),
        "random_forest": Pipeline([
            ("imputer", IterativeImputer(random_state=RANDOM_STATE, max_iter=10)),
            ("scaler", StandardScaler()),  # RF doesn't need scaling; kept for a uniform predict(raw_features) interface across all 3 models
            ("clf", RandomForestClassifier(
                n_estimators=300,
                max_depth=4,
                min_samples_leaf=8,
                max_features="sqrt",
                class_weight="balanced",
                random_state=RANDOM_STATE,
                n_jobs=-1,
            )),
        ]),
        "xgboost": Pipeline([
            ("imputer", IterativeImputer(random_state=RANDOM_STATE, max_iter=10)),
            ("scaler", StandardScaler()),
            ("clf", XGBClassifier(
                n_estimators=150,
                max_depth=3,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_lambda=2.0,
                reg_alpha=0.5,
                min_child_weight=5,
                scale_pos_weight=scale_pos_weight,
                eval_metric="logloss",
                random_state=RANDOM_STATE,
                n_jobs=-1,
            )),
        ]),
    }


def ci_summary(fold_scores: np.ndarray) -> dict:
    """Mean + 95% CI (t-distribution, df=n-1) across a small number of CV folds."""
    n = len(fold_scores)
    mean = float(np.mean(fold_scores))
    std = float(np.std(fold_scores, ddof=1))
    sem = std / np.sqrt(n) if n > 1 else 0.0
    t_crit = stats.t.ppf(0.975, df=n - 1) if n > 1 else 0.0
    margin = t_crit * sem
    return {
        "fold_scores": [round(float(s), 4) for s in fold_scores],
        "mean": round(mean, 4),
        "std": round(std, 4),
        "ci95_lower": round(mean - margin, 4),
        "ci95_upper": round(mean + margin, 4),
    }


def evaluate_model(pipeline: Pipeline, X: pd.DataFrame, y: pd.Series, cv) -> dict:
    raw = cross_validate(pipeline, X, y, cv=cv, scoring=SCORING, n_jobs=1)

    summary = {
        "roc_auc": ci_summary(raw["test_roc_auc"]),
        "precision": ci_summary(raw["test_precision"]),
        "recall": ci_summary(raw["test_recall"]),
        "f1": ci_summary(raw["test_f1"]),
        # neg_brier_score is negative-oriented (higher=better) so scikit-learn's
        # "greater is better" convention holds; flip sign back so this reads as
        # an actual Brier score, where LOWER is better (0 = perfect calibration).
        "brier_score": ci_summary(-raw["test_neg_brier_score"]),
    }
    return summary


def _dig(d: dict, path: tuple):
    for key in path:
        d = d[key]
    return d


def select_winner(all_results: dict) -> tuple:
    """Pick the winning model using a documented rule, not a bare argmax.

    Primary criterion: highest mean ROC-AUC. But with n=5 folds on a
    329-patient cohort, small ROC-AUC gaps aren't statistically
    distinguishable -- if the top model's 95% CI lower bound doesn't clear
    every other model's mean, picking it on point estimate alone would be
    reading noise as a decision. In that case, fall through to tie-breakers
    in this order (each one clinically/statistically motivated for a
    severe-event risk model):
        1. Brier score -- calibration: a well-calibrated probability is
                more clinically actionable than a merely
                well-ranked one, and this is a risk score tool.

        2. Recall      -- missing a real severe-event patient (false
                negative) is the costlier clinical error, so a
                model that catches more true positives is
                preferred among near-equal ROC-AUC performers.

        3. Precision   -- among models tied so far, prefer fewer false alarms.

        4. Recall std  -- prefer the model whose recall is more stable
                across folds.

    Returns (winner_name, reason_string).
    """
    names = list(all_results.keys())
    roc_mean = {n: all_results[n]["roc_auc"]["mean"] for n in names}
    roc_lower = {n: all_results[n]["roc_auc"]["ci95_lower"] for n in names}

    top = max(names, key=lambda n: roc_mean[n])
    clearly_separated = all(
        roc_lower[top] > roc_mean[n] for n in names if n != top
    )
    if clearly_separated:
        return top, "highest mean ROC-AUC, 95% CI clearly separated from all other models"

    # CIs overlap -> point estimate alone isn't decisive. Fall through the
    # clinical tie-break chain among ALL models (overlap means none is
    # statistically ruled out by ROC-AUC alone).
    contenders = names
    for metric_path, better, label in [
    (("brier_score", "mean"), "min", "calibration (Brier)"),
    (("recall", "mean"), "max", "recall"),
    (("precision", "mean"), "max", "precision"),
    (("recall", "std"), "min", "recall stability (std)"),
]:
        vals = {n: _dig(all_results[n], metric_path) for n in contenders}
        best = max(vals.values()) if better == "max" else min(vals.values())
        tied = [n for n in contenders if round(vals[n], 4) == round(best, 4)]
        if len(tied) == 1:
            return tied[0], f"ROC-AUC CIs overlap (not statistically separable); tie-broken on {label}"
        contenders = tied

    return top, "ROC-AUC CIs overlap and all tie-breakers exhausted; defaulted to highest mean ROC-AUC"


def print_report(all_results: dict) -> None:
    print("\n" + "=" * 72)
    print("5-FOLD CV RESULTS (mean [95% CI])")
    print("=" * 72)
    header = f"{'model':22s}{'roc_auc':>16s}{'precision':>14s}{'recall':>12s}{'f1':>12s}{'brier':>12s}"
    print(header)
    for name, res in all_results.items():
        row = (
            f"{name:22s}"
            f"{res['roc_auc']['mean']:>9.4f} \u00b1{(res['roc_auc']['ci95_upper']-res['roc_auc']['mean']):.3f}"
            f"{res['precision']['mean']:>9.3f}"
            f"{res['recall']['mean']:>8.3f}"
            f"{res['f1']['mean']:>8.3f}"
            f"{res['brier_score']['mean']:>8.3f} (lower=better)"
        )
        print(row)
    print("(brier score: lower is better; all other metrics: higher is better)")


def main():
    df = pd.read_csv(INPUT_PATH)
    features, ids, target = build_feature_frame(df)

    n_pos = int((target == 1).sum())
    n_neg = int((target == 0).sum())
    scale_pos_weight = n_neg / n_pos

    print(f"Cohort: {len(target)} patients | severe_event=1: {n_pos} | severe_event=0: {n_neg}")
    print(f"Features ({len(features.columns)}): {list(features.columns)}")

    cv = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    pipelines = build_pipelines(scale_pos_weight=scale_pos_weight)

    all_results = {}
    for name, pipe in pipelines.items():
        print(f"\nRunning {N_FOLDS}-fold CV for {name}...")
        all_results[name] = evaluate_model(pipe, features, target, cv)

    print_report(all_results)

    winner_name, winner_reason = select_winner(all_results)
    print(f"\nWinner: {winner_name}  ({winner_reason})")

    os.makedirs(MODELS_DIR, exist_ok=True)

    fitted = {}
    for name, pipe in pipelines.items():
        pipe.fit(features, target)  # final fit on the FULL 329-patient cohort
        fitted[name] = pipe
        out_path = os.path.join(MODELS_DIR, f"{SHORT_NAMES[name]}_model.pkl")
        joblib.dump(pipe, out_path)
        print(f"Saved {name} -> {out_path}")

    winner_path = os.path.join(MODELS_DIR, "model.pkl")
    joblib.dump(fitted[winner_name], winner_path)
    print(f"Saved winning model ({winner_name}) -> {winner_path}  (this is what backend/main.py loads)")

    metrics_out = {
        "cohort_size": int(len(target)),
        "class_balance": {"severe_event=0": n_neg, "severe_event=1": n_pos},
        "cv_folds": N_FOLDS,
        "feature_columns": list(features.columns),
        "results": all_results,
        "winner": winner_name,
        "winner_selection_criterion": winner_reason,
    }
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics_out, f, indent=2)
    print(f"Saved metrics summary -> {METRICS_PATH}")


if __name__ == "__main__":
    main()