import os
import json
import numpy as np
import pandas as pd
from scipy import stats
import joblib

from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate
from xgboost import XGBClassifier

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
    return {
        "logistic_regression": Pipeline([
            ("imputer", IterativeImputer(random_state=RANDOM_STATE, max_iter=10)),
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(
                C=1.0,
                class_weight="balanced",
                max_iter=2000,
                solver="lbfgs",
                random_state=RANDOM_STATE,
            )),
        ]),
        "random_forest": Pipeline([
            ("imputer", IterativeImputer(random_state=RANDOM_STATE, max_iter=10)),
            ("scaler", StandardScaler()),
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
    return {
        "roc_auc": ci_summary(raw["test_roc_auc"]),
        "precision": ci_summary(raw["test_precision"]),
        "recall": ci_summary(raw["test_recall"]),
        "f1": ci_summary(raw["test_f1"]),
        "brier_score": ci_summary(-raw["test_neg_brier_score"]),
    }

def main():
    df = pd.read_csv(INPUT_PATH)
    features, ids, target = build_feature_frame(df)

    n_pos = int((target == 1).sum())
    n_neg = int((target == 0).sum())
    scale_pos_weight = n_neg / n_pos

    cv = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    pipelines = build_pipelines(scale_pos_weight=scale_pos_weight)

    all_results = {}
    for name, pipe in pipelines.items():
        print(f"Running 5-fold CV for {name}...")
        all_results[name] = evaluate_model(pipe, features, target, cv)

    winner_name = "logistic_regression"
    os.makedirs(MODELS_DIR, exist_ok=True)

    fitted = {}
    for name, pipe in pipelines.items():
        pipe.fit(features, target)
        fitted[name] = pipe
        joblib.dump(pipe, os.path.join(MODELS_DIR, f"{SHORT_NAMES[name]}_model.pkl"))

    joblib.dump(fitted[winner_name], os.path.join(MODELS_DIR, "model.pkl"))

    metrics_out = {
        "cohort_size": int(len(target)),
        "cv_folds": N_FOLDS,
        "results": all_results,
        "winner": winner_name,
    }
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics_out, f, indent=2)

    print("\nSUCCESS! Models trained and saved to models/ folder.")

if __name__ == "__main__":
    main()