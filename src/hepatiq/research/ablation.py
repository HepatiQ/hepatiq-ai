"""Leakage-safe feature ablation, repeated CV, optimism and held-out analysis."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer, MissingIndicator
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import learning_curve
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import StandardScaler

from hepatiq.research.config import (
    ALL_FEATURES,
    FEATURE_SETS,
    N_FOLDS,
    N_OPTIMISM_RESAMPLES,
    PRIMARY_SEED,
    REPEATED_SEEDS,
)
from hepatiq.research.data import (
    ResearchCohort,
    heldout_indices,
    select_features,
    stratified_folds,
)
from hepatiq.research.metrics import (
    auc_score,
    brier_score,
    calibration_slope_intercept,
    evaluate_probabilities,
    paired_bootstrap_difference,
)

MODEL_NAMES = ("lr", "rf", "xgb")


def _iterative_imputer(seed: int) -> IterativeImputer:
    return IterativeImputer(random_state=seed, max_iter=10, initial_strategy="mean")


def _preprocessor(add_indicators: bool, seed: int):
    if not add_indicators:
        return _iterative_imputer(seed)
    return FeatureUnion(
        [
            ("imputed", _iterative_imputer(seed)),
            ("missing", MissingIndicator(features="all")),
        ]
    )


def make_pipeline(
    model_name: str = "lr",
    *,
    weighted: bool = True,
    add_indicators: bool = False,
    seed: int = PRIMARY_SEED,
    scale_pos_weight: float = 1.0,
) -> Pipeline:
    if model_name not in MODEL_NAMES:
        raise ValueError(f"unknown model {model_name!r}; expected one of {MODEL_NAMES}")

    steps: list[tuple[str, object]] = [("preprocess", _preprocessor(add_indicators, seed))]
    steps.append(("scaler", StandardScaler()))

    if model_name == "lr":
        clf = LogisticRegression(
            C=1.0,
            class_weight="balanced" if weighted else None,
            max_iter=2000,
            solver="lbfgs",
            random_state=seed,
        )
    elif model_name == "rf":
        clf = RandomForestClassifier(
            n_estimators=300,
            max_depth=4,
            min_samples_leaf=8,
            max_features="sqrt",
            class_weight="balanced" if weighted else None,
            random_state=seed,
            n_jobs=1,
        )
    else:
        from xgboost import XGBClassifier

        clf = XGBClassifier(
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
            random_state=seed,
            n_jobs=1,
        )

    steps.append(("clf", clf))
    return Pipeline(steps)


def _feature_matrix(cohort: ResearchCohort, feature_names: Sequence[str]) -> pd.DataFrame:
    return select_features(cohort.features, tuple(feature_names)).reset_index(drop=True)


def run_oof(
    cohort: ResearchCohort,
    feature_names: Sequence[str] = ALL_FEATURES,
    *,
    model_name: str = "lr",
    weighted: bool = True,
    add_indicators: bool = False,
    seed: int = PRIMARY_SEED,
    n_folds: int = N_FOLDS,
) -> dict[str, object]:
    """Fit a fresh pipeline in every fold and return one prediction per patient."""
    features = _feature_matrix(cohort, feature_names)
    target = cohort.target.reset_index(drop=True)
    folds = stratified_folds(target, n_folds=n_folds, seed=seed)
    oof = np.full(len(target), np.nan, dtype=float)
    fold_ids = np.full(len(target), -1, dtype=int)

    for fold, (train_idx, test_idx) in enumerate(folds):
        pipeline = make_pipeline(
            model_name,
            weighted=weighted,
            add_indicators=add_indicators,
            seed=seed,
            scale_pos_weight=_scale_pos_weight(target.iloc[train_idx]),
        )
        pipeline.fit(features.iloc[train_idx], target.iloc[train_idx])
        oof[test_idx] = pipeline.predict_proba(features.iloc[test_idx])[:, 1]
        fold_ids[test_idx] = fold

    if np.isnan(oof).any():
        raise ValueError("out-of-fold predictions contain missing values")
    return {
        "y_true": target.to_numpy(),
        "y_prob": oof,
        "fold": fold_ids,
        "feature_names": list(feature_names),
        "model_name": model_name,
        "weighted": weighted,
        "add_indicators": add_indicators,
        "seed": seed,
        "n_folds": n_folds,
    }


def _scale_pos_weight(target: pd.Series) -> float:
    positives = int((target == 1).sum())
    negatives = int((target == 0).sum())
    return float(negatives / positives) if positives else 1.0


def summarize_oof(result: dict[str, object]) -> dict[str, object]:
    summary = evaluate_probabilities(result["y_true"], result["y_prob"])
    summary.update(
        {
            "feature_names": result["feature_names"],
            "model_name": result["model_name"],
            "weighted": result["weighted"],
            "add_indicators": result["add_indicators"],
            "seed": result["seed"],
        }
    )
    return summary


def repeated_oof(
    cohort: ResearchCohort,
    feature_names: Sequence[str] = ALL_FEATURES,
    *,
    model_name: str = "lr",
    weighted: bool = True,
    add_indicators: bool = False,
    seeds: Sequence[int] = REPEATED_SEEDS,
) -> list[dict[str, object]]:
    return [
        run_oof(
            cohort,
            feature_names,
            model_name=model_name,
            weighted=weighted,
            add_indicators=add_indicators,
            seed=seed,
        )
        for seed in seeds
    ]


def repeated_summary(results: Sequence[dict[str, object]]) -> dict[str, object]:
    summaries = [evaluate_probabilities(result["y_true"], result["y_prob"]) for result in results]
    metrics = ("auc", "brier")
    out: dict[str, object] = {"n_repeats": len(summaries), "metrics": {}}
    for metric in metrics:
        points = np.asarray([summary[metric]["point"] for summary in summaries], dtype=float)
        out["metrics"][metric] = {
            "mean": float(points.mean()),
            "sd": float(points.std(ddof=1)) if len(points) > 1 else 0.0,
            "min": float(points.min()),
            "max": float(points.max()),
        }
    slopes = np.asarray([summary["calibration_slope"] for summary in summaries], dtype=float)
    out["metrics"]["calibration_slope"] = {
        "mean": float(np.nanmean(slopes)),
        "sd": float(np.nanstd(slopes, ddof=1)) if len(slopes) > 1 else 0.0,
        "min": float(np.nanmin(slopes)),
        "max": float(np.nanmax(slopes)),
    }
    return out


def run_feature_set_suite(
    cohort: ResearchCohort,
    *,
    seeds: Sequence[int] = (PRIMARY_SEED,),
    model_name: str = "lr",
) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for feature_set, names in FEATURE_SETS.items():
        for weighted in (True, False):
            if model_name != "lr" and not weighted:
                continue
            result = run_oof(
                cohort,
                names,
                model_name=model_name,
                weighted=weighted,
                add_indicators=feature_set == "F17+IND",
                seed=seeds[0],
            )
            key = f"{feature_set}|{'weighted' if weighted else 'unweighted'}"
            out[key] = {
                "summary": summarize_oof(result),
                "repeated": repeated_summary(
                    [
                        run_oof(
                            cohort,
                            names,
                            model_name=model_name,
                            weighted=weighted,
                            add_indicators=feature_set == "F17+IND",
                            seed=seed,
                        )
                        for seed in seeds
                    ]
                ),
            }
    return out


def _slope_metric(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    return calibration_slope_intercept(y_true, y_prob)[0]


def compare_predictions(
    y_true,
    prob_reference,
    prob_comparator,
    *,
    n_boot: int,
    seed: int = PRIMARY_SEED,
) -> dict[str, object]:
    return {
        "delta_auc": paired_bootstrap_difference(
            y_true, prob_reference, prob_comparator, auc_score, n_boot=n_boot, seed=seed
        ),
        "delta_brier": paired_bootstrap_difference(
            y_true, prob_reference, prob_comparator, brier_score, n_boot=n_boot, seed=seed
        ),
        "delta_calibration_slope": paired_bootstrap_difference(
            y_true, prob_reference, prob_comparator, _slope_metric, n_boot=n_boot, seed=seed
        ),
    }


def optimism_correction(
    cohort: ResearchCohort,
    feature_names: Sequence[str] = ALL_FEATURES,
    *,
    metric_fn: Callable[[np.ndarray, np.ndarray], float] = auc_score,
    model_name: str = "lr",
    weighted: bool = True,
    add_indicators: bool = False,
    n_resamples: int = N_OPTIMISM_RESAMPLES,
    seed: int = PRIMARY_SEED,
) -> dict[str, object]:
    """Stratified bootstrap optimism for one pre-specified metric."""
    features = _feature_matrix(cohort, feature_names)
    target = cohort.target.reset_index(drop=True)
    y = target.to_numpy()
    pipeline = make_pipeline(
        model_name,
        weighted=weighted,
        add_indicators=add_indicators,
        seed=seed,
        scale_pos_weight=_scale_pos_weight(target),
    )
    pipeline.fit(features, target)
    apparent = float(metric_fn(y, pipeline.predict_proba(features)[:, 1]))

    positive = np.flatnonzero(y == 1)
    negative = np.flatnonzero(y == 0)
    rng = np.random.RandomState(seed)
    optimism: list[float] = []
    for _ in range(n_resamples):
        idx = np.concatenate(
            [
                rng.choice(positive, size=len(positive), replace=True),
                rng.choice(negative, size=len(negative), replace=True),
            ]
        )
        rng.shuffle(idx)
        y_boot = y[idx]
        try:
            boot_pipe = make_pipeline(
                model_name,
                weighted=weighted,
                add_indicators=add_indicators,
                seed=seed,
                scale_pos_weight=_scale_pos_weight(pd.Series(y_boot)),
            )
            boot_pipe.fit(features.iloc[idx], pd.Series(y_boot))
            apparent_boot = float(metric_fn(y_boot, boot_pipe.predict_proba(features.iloc[idx])[:, 1]))
            test_boot = float(metric_fn(y, boot_pipe.predict_proba(features)[:, 1]))
            optimism.append(apparent_boot - test_boot)
        except ValueError:
            continue

    if not optimism:
        raise ValueError("no valid bootstrap resamples for optimism correction")
    mean_optimism = float(np.mean(optimism))
    return {
        "metric": getattr(metric_fn, "__name__", "metric"),
        "apparent": apparent,
        "mean_optimism": mean_optimism,
        "optimism_corrected": apparent - mean_optimism,
        "n_resamples": len(optimism),
    }


def _calibration_slope(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    return float(calibration_slope_intercept(y_true, y_prob)[0])


def _calibration_intercept(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    return float(calibration_slope_intercept(y_true, y_prob)[1])


def optimism_correction_multi(
    cohort: ResearchCohort,
    feature_names: Sequence[str] = ALL_FEATURES,
    *,
    metric_fns: Mapping[str, Callable[[np.ndarray, np.ndarray], float]],
    model_name: str = "lr",
    weighted: bool = True,
    add_indicators: bool = False,
    n_resamples: int = N_OPTIMISM_RESAMPLES,
    seed: int = PRIMARY_SEED,
) -> dict[str, object]:
    """Stratified bootstrap optimism for several metrics from one refit loop."""
    features = _feature_matrix(cohort, feature_names)
    target = cohort.target.reset_index(drop=True)
    y = target.to_numpy()
    pipeline = make_pipeline(
        model_name,
        weighted=weighted,
        add_indicators=add_indicators,
        seed=seed,
        scale_pos_weight=_scale_pos_weight(target),
    )
    pipeline.fit(features, target)
    apparent_probs = pipeline.predict_proba(features)[:, 1]
    apparent = {name: float(fn(y, apparent_probs)) for name, fn in metric_fns.items()}

    positive = np.flatnonzero(y == 1)
    negative = np.flatnonzero(y == 0)
    rng = np.random.RandomState(seed)
    optimism: dict[str, list[float]] = {name: [] for name in metric_fns}
    n_valid = 0
    for _ in range(n_resamples):
        idx = np.concatenate(
            [
                rng.choice(positive, size=len(positive), replace=True),
                rng.choice(negative, size=len(negative), replace=True),
            ]
        )
        rng.shuffle(idx)
        y_boot = y[idx]
        try:
            boot_pipe = make_pipeline(
                model_name,
                weighted=weighted,
                add_indicators=add_indicators,
                seed=seed,
                scale_pos_weight=_scale_pos_weight(pd.Series(y_boot)),
            )
            boot_pipe.fit(features.iloc[idx], pd.Series(y_boot))
            apparent_boot_probs = boot_pipe.predict_proba(features.iloc[idx])[:, 1]
            test_boot_probs = boot_pipe.predict_proba(features)[:, 1]
            values = {
                name: float(fn(y_boot, apparent_boot_probs) - fn(y, test_boot_probs))
                for name, fn in metric_fns.items()
            }
        except ValueError:
            continue
        for name, value in values.items():
            optimism[name].append(value)
        n_valid += 1

    if n_valid == 0:
        raise ValueError("no valid bootstrap resamples for optimism correction")
    return {
        name: {
            "apparent": apparent[name],
            "mean_optimism": float(np.mean(values)),
            "optimism_corrected": apparent[name] - float(np.mean(values)),
            "n_resamples": len(values),
        }
        for name, values in optimism.items()
    }


def collinearity_diagnostics(
    cohort: ResearchCohort,
    feature_names: Sequence[str] = ALL_FEATURES,
) -> dict[str, object]:
    """Condition number and VIF on a full-cohort imputed design matrix.

    This is a structural diagnostic, not a validation estimate. It reuses the
    full cohort only to describe feature redundancy.
    """
    import warnings

    features = _feature_matrix(cohort, feature_names)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        values = _iterative_imputer(PRIMARY_SEED).fit_transform(features)
    values = np.asarray(values, dtype=float)
    sd = values.std(axis=0, ddof=1)
    if np.any(sd == 0):
        raise ValueError("cannot compute collinearity with a constant feature")
    standardized = (values - values.mean(axis=0)) / sd
    corr = np.corrcoef(standardized, rowvar=False)
    vif = np.diag(np.linalg.pinv(corr))
    return {
        "condition_number": float(np.linalg.cond(standardized)),
        "vif": {name: float(value) for name, value in zip(feature_names, vif, strict=True)},
        "note": "full-cohort imputed design matrix; structural diagnostic only",
    }


def coefficient_stability(
    cohort: ResearchCohort,
    feature_names: Sequence[str] = ALL_FEATURES,
    *,
    seeds: Sequence[int] = REPEATED_SEEDS,
) -> pd.DataFrame:
    """Standardized LR coefficients across repeated folds, not bootstrap draws."""
    features = _feature_matrix(cohort, feature_names)
    target = cohort.target.reset_index(drop=True)
    rows: list[np.ndarray] = []
    for seed in seeds:
        for train_idx, _ in stratified_folds(target, seed=seed):
            pipeline = make_pipeline("lr", weighted=True, seed=seed)
            pipeline.fit(features.iloc[train_idx], target.iloc[train_idx])
            coef = np.asarray(pipeline.named_steps["clf"].coef_[0], dtype=float)
            if coef.size == len(feature_names):
                rows.append(coef)

    if not rows:
        raise ValueError("no coefficient vectors collected")
    matrix = np.vstack(rows)
    return pd.DataFrame(
        {
            "feature": list(feature_names),
            "mean": matrix.mean(axis=0),
            "sd": matrix.std(axis=0, ddof=1),
            "sign_consistency": np.where(matrix > 0, 1.0, np.where(matrix < 0, -1.0, 0.0)).mean(axis=0),
            "n_fits": matrix.shape[0],
        }
    )


def learning_curve_summary(
    cohort: ResearchCohort,
    feature_names: Sequence[str] = ALL_FEATURES,
    *,
    weighted: bool = True,
    seed: int = PRIMARY_SEED,
) -> dict[str, object]:
    features = _feature_matrix(cohort, feature_names)
    target = cohort.target.reset_index(drop=True)
    sizes, train_scores, test_scores = learning_curve(
        make_pipeline("lr", weighted=weighted, seed=seed),
        features,
        target,
        train_sizes=np.linspace(0.2, 1.0, 5),
        scoring="roc_auc",
        cv=stratified_folds(target, seed=seed),
        n_jobs=1,
        shuffle=False,
    )
    return {
        "train_sizes": sizes.tolist(),
        "train_mean": train_scores.mean(axis=1).tolist(),
        "test_mean": test_scores.mean(axis=1).tolist(),
    }


def heldout_evaluation(
    cohort: ResearchCohort,
    feature_names: Sequence[str] = ALL_FEATURES,
    *,
    weighted: bool = True,
    add_indicators: bool = False,
    seed: int = PRIMARY_SEED,
) -> dict[str, object]:
    """Train on randomized patients, test once on non-randomized patients."""
    derivation, validation = heldout_indices(cohort.frame)
    features = select_features(cohort.features, tuple(feature_names))
    target = cohort.target

    train_x = features.loc[derivation]
    train_y = target.loc[derivation]
    test_x = features.loc[validation]
    test_y = target.loc[validation]

    pipeline = make_pipeline(
        "lr",
        weighted=weighted,
        add_indicators=add_indicators,
        seed=seed,
        scale_pos_weight=_scale_pos_weight(train_y),
    )
    pipeline.fit(train_x, train_y)
    probabilities = pipeline.predict_proba(test_x)[:, 1]
    summary = evaluate_probabilities(test_y.to_numpy(), probabilities)
    summary.update(
        {
            "train_n": int(len(train_y)),
            "train_events": int(train_y.sum()),
            "test_n": int(len(test_y)),
            "test_events": int(test_y.sum()),
            "note": "internal 312/106 cohort split; not external validation",
        }
    )
    return summary
