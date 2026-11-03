"""Patient-level imputation sensitivity and multiple-imputation summaries."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer
from sklearn.pipeline import FeatureUnion

from hepatiq.paths import MODEL_PATH
from hepatiq.research.config import (
    ALL_FEATURES,
    CLINICALLY_NORMAL_OPTIONAL,
    IMPUTED_OPTIONAL_FEATURES,
    OBSERVED_PATIENT_FIELDS,
    PATIENT_B,
    PATIENT_B_EXPECTED,
    RISK_BANDS,
)


def load_model(path: str | Path = MODEL_PATH):
    return joblib.load(path)


def model_feature_names(model) -> tuple[str, ...]:
    names = getattr(model, "feature_names_in_", None)
    if names is None:
        return ALL_FEATURES
    return tuple(str(name) for name in names)


REQUIRED_OBSERVED = ("age", "bili", "albumin", "edema")


def encode_patient(payload: dict, feature_names: tuple[str, ...] = ALL_FEATURES) -> pd.DataFrame:
    """Build one complete-schema row; optional values stay NaN for imputation."""
    missing_required = [name for name in REQUIRED_OBSERVED if payload.get(name) is None]
    if missing_required:
        raise ValueError(f"patient payload is missing required fields: {missing_required}")
    if "sex" in feature_names and payload.get("sex") is None:
        raise ValueError("patient payload is missing required field: sex")

    row = {name: np.nan for name in ALL_FEATURES}
    for name in ALL_FEATURES:
        if name in payload and payload[name] is not None:
            row[name] = payload[name]

    if "sex" in feature_names:
        sex = payload.get("sex")
        if isinstance(sex, str):
            sex = sex.strip().lower()
            if sex not in {"f", "m"}:
                raise ValueError("sex must be 'f' or 'm'")
            row["sex"] = 0.0 if sex == "f" else 1.0
        elif not np.isfinite(sex) or sex not in (0.0, 1.0):
            raise ValueError("sex must be 'f' or 'm'")

    if row["age"] <= 0:
        raise ValueError("age must be positive")
    if row["bili"] <= 0:
        raise ValueError("bili must be positive")
    if row["albumin"] <= 0:
        raise ValueError("albumin must be positive")
    if row["edema"] not in (0.0, 0.5, 1.0):
        raise ValueError("edema must be 0, 0.5 or 1")
    if "protime" in feature_names and pd.notna(row["protime"]) and row["protime"] <= 0:
        raise ValueError("protime must be positive when provided")

    return pd.DataFrame([row], columns=list(feature_names))


def predict_patient(model, payload: dict, feature_names: tuple[str, ...] | None = None) -> float:
    names = feature_names or model_feature_names(model)
    row = encode_patient(payload, names)
    return float(model.predict_proba(row)[:, 1][0])


def _find_imputer(model) -> IterativeImputer:
    preprocess = model.named_steps.get("preprocess") or model.named_steps.get("imputer")
    if preprocess is None:
        raise ValueError("model has no preprocess or imputer step")
    if isinstance(preprocess, FeatureUnion):
        for name, transformer in preprocess.transformer_list:
            if name == "imputed":
                return transformer
        raise ValueError("FeatureUnion has no imputed transformer")
    if not isinstance(preprocess, IterativeImputer):
        raise ValueError(f"unexpected preprocess step: {type(preprocess).__name__}")
    return preprocess


def imputed_values(model, payload: dict) -> pd.Series:
    names = model_feature_names(model)
    row = encode_patient(payload, names)
    imputer = _find_imputer(model)
    values = imputer.transform(row)
    return pd.Series(values[0], index=list(names), name="imputed_value")


def cohort_typical_values(features: pd.DataFrame) -> dict[str, float]:
    return {name: float(features[name].median()) for name in ALL_FEATURES if name in features.columns}


def percentile_values(features: pd.DataFrame, quantile: float) -> dict[str, float]:
    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be in [0, 1]")
    return {name: float(features[name].quantile(quantile)) for name in ALL_FEATURES if name in features.columns}


def _base_payload() -> dict:
    return dict(PATIENT_B)


def _with_optional(base: dict, optional: dict[str, float]) -> dict:
    payload = dict(base)
    payload.update(optional)
    return payload


def _imputed_only(values: dict[str, float]) -> dict[str, float]:
    return {name: value for name, value in values.items() if name in IMPUTED_OPTIONAL_FEATURES}


def patient_b_scenarios(features: pd.DataFrame) -> dict[str, dict]:
    typical = _imputed_only(cohort_typical_values(features))
    p10 = _imputed_only(percentile_values(features, 0.10))
    p50 = _imputed_only(percentile_values(features, 0.50))
    p90 = _imputed_only(percentile_values(features, 0.90))
    normal = _imputed_only(CLINICALLY_NORMAL_OPTIONAL)
    base = _base_payload()

    scenarios = {
        "only_observed": dict(base),
        "cohort_typical": _with_optional(base, typical),
        "clinically_normal": _with_optional(base, normal),
        "p10_optional": _with_optional(base, p10),
        "p50_optional": _with_optional(base, p50),
        "p90_optional": _with_optional(base, p90),
    }
    scenarios["protime_10_8"] = _with_optional(base, {"protime": 10.8})
    scenarios["stage_3"] = _with_optional(base, {"stage": 3.0})
    scenarios["age_60"] = _with_optional(base, {"age": 60.0})
    scenarios["albumin_3_4"] = _with_optional(base, {"albumin": 3.4})
    scenarios["bili_1_1"] = _with_optional(base, {"bili": 1.1})
    return scenarios


def patient_b_sensitivity(model, features: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scenario, payload in patient_b_scenarios(features).items():
        rows.append(
            {
                "scenario": scenario,
                "prediction": predict_patient(model, payload),
            }
        )
    out = pd.DataFrame(rows)
    out["delta_pp"] = (out["prediction"] - predict_patient(model, _base_payload())) * 100.0
    return out


def tornado(model, features: pd.DataFrame) -> pd.DataFrame:
    """One-feature-at-a-time sensitivity for every optional input."""
    base = _base_payload()
    baseline = predict_patient(model, base)
    typical = cohort_typical_values(features)
    p10 = percentile_values(features, 0.10)
    p50 = percentile_values(features, 0.50)
    p90 = percentile_values(features, 0.90)

    rows = []
    for feature in IMPUTED_OPTIONAL_FEATURES:
        if feature not in features.columns:
            continue
        values = {
            "p10": p10[feature],
            "p50": p50[feature],
            "p90": p90[feature],
            "clinically_normal": CLINICALLY_NORMAL_OPTIONAL[feature],
            "cohort_typical": typical[feature],
        }
        for label, value in values.items():
            prediction = predict_patient(model, _with_optional(base, {feature: value}))
            rows.append(
                {
                    "feature": feature,
                    "scenario": label,
                    "value": value,
                    "prediction": prediction,
                    "delta_pp": (prediction - baseline) * 100.0,
                }
            )
    return pd.DataFrame(rows)


def risk_band(probability: float) -> str:
    for name, lower, upper in RISK_BANDS:
        if lower <= probability < upper:
            return name
    return RISK_BANDS[-1][0]


def _predict_completed(model, completed: np.ndarray) -> np.ndarray:
    scaler = model.named_steps.get("scaler")
    clf = model.named_steps.get("clf")
    if scaler is None or clf is None:
        raise ValueError("model must expose scaler and clf steps")
    return clf.predict_proba(scaler.transform(completed))[:, 1]


def multiple_imputation_predictions(
    model,
    payload: dict,
    training_features: pd.DataFrame,
    *,
    n_imputations: int = 20,
    seed: int = 42,
) -> np.ndarray:
    """Sample posterior imputations, then apply the deployed scaler and model."""
    if n_imputations < 1:
        raise ValueError("n_imputations must be positive")

    names = model_feature_names(model)
    train = training_features.loc[:, list(names)]
    row = encode_patient(payload, names)

    predictions: list[float] = []
    for draw in range(n_imputations):
        imputer = IterativeImputer(
            random_state=seed + draw,
            max_iter=10,
            sample_posterior=True,
        )
        imputer.fit(train)
        completed = imputer.transform(row)
        predictions.append(float(_predict_completed(model, completed)[0]))
    return np.asarray(predictions, dtype=float)


def summarize_predictions(predictions: np.ndarray) -> dict[str, object]:
    values = np.asarray(predictions, dtype=float)
    bands = [risk_band(value) for value in values]
    return {
        "n": int(values.size),
        "mean": float(values.mean()),
        "sd": float(values.std(ddof=1)) if values.size > 1 else 0.0,
        "min": float(values.min()),
        "max": float(values.max()),
        "q10": float(np.quantile(values, 0.10)),
        "q50": float(np.quantile(values, 0.50)),
        "q90": float(np.quantile(values, 0.90)),
        "range_pp": float((values.max() - values.min()) * 100.0),
        "band_counts": {name: bands.count(name) for name, _, _ in RISK_BANDS},
    }


def _observed_matrix(frame: pd.DataFrame, names: tuple[str, ...]) -> pd.DataFrame:
    matrix = pd.DataFrame(np.nan, index=range(len(frame)), columns=list(names))
    for field in OBSERVED_PATIENT_FIELDS:
        if field in matrix.columns:
            matrix[field] = frame[field].to_numpy(dtype=float)
    return matrix


def _all_patient_scenarios(features: pd.DataFrame) -> dict[str, dict[str, float]]:
    typical = _imputed_only(cohort_typical_values(features))
    p10 = _imputed_only(percentile_values(features, 0.10))
    p90 = _imputed_only(percentile_values(features, 0.90))
    normal = _imputed_only(CLINICALLY_NORMAL_OPTIONAL)
    return {
        "only_observed": {},
        "cohort_typical": typical,
        "clinically_normal": normal,
        "p10_optional": p10,
        "p90_optional": p90,
    }


def all_patient_sensitivity(
    model,
    frame: pd.DataFrame,
    features: pd.DataFrame,
    *,
    n_imputations: int = 20,
    seed: int = 42,
) -> dict[str, object]:
    """Apply the five-input workflow to every labeled patient and vary imputations."""
    features = features.reset_index(drop=True)
    frame = frame.reset_index(drop=True)
    names = model_feature_names(model)
    base = _observed_matrix(features, names)
    baseline = model.predict_proba(base)[:, 1]

    scenario_predictions: dict[str, np.ndarray] = {}
    for name, values in _all_patient_scenarios(features).items():
        matrix = base.copy()
        for feature, value in values.items():
            matrix[feature] = value
        scenario_predictions[name] = model.predict_proba(matrix)[:, 1]

    scenario_summary = {
        name: {
            **summarize_predictions(predictions),
            "mean_delta_vs_plugin": float(np.mean(predictions - baseline)),
        }
        for name, predictions in scenario_predictions.items()
    }
    per_patient_range = np.max(np.column_stack(list(scenario_predictions.values())), axis=1) - np.min(
        np.column_stack(list(scenario_predictions.values())), axis=1
    )

    train = features.loc[:, list(names)]
    draws = np.empty((len(frame), n_imputations), dtype=float)
    for draw in range(n_imputations):
        imputer = IterativeImputer(
            random_state=seed + draw,
            max_iter=10,
            sample_posterior=True,
        )
        imputer.fit(train)
        completed = imputer.transform(base)
        draws[:, draw] = _predict_completed(model, completed)

    mi_mean = draws.mean(axis=1)
    mi_sd = draws.std(axis=1, ddof=1)
    baseline_bands = np.array([risk_band(value) for value in baseline])
    mean_bands = np.array([risk_band(value) for value in mi_mean])
    any_draw_change = np.array(
        [any(risk_band(value) != band for value in row) for row, band in zip(draws, baseline_bands, strict=True)]
    )
    randomized = frame["trt"].notna().to_numpy()

    def group_summary(mask: np.ndarray) -> dict[str, object]:
        return {
            "n": int(mask.sum()),
            "mean_scenario_range_pp": float(per_patient_range[mask].mean() * 100.0),
            "mean_mi_sd_pp": float(mi_sd[mask].mean() * 100.0),
            "mean_band_change_rate": float(np.mean(baseline_bands[mask] != mean_bands[mask])),
            "any_draw_band_change_rate": float(any_draw_change[mask].mean()),
        }

    return {
        "n": int(len(frame)),
        "baseline_bands": {name: int((baseline_bands == name).sum()) for name, _, _ in RISK_BANDS},
        "mean_mi_bands": {name: int((mean_bands == name).sum()) for name, _, _ in RISK_BANDS},
        "mean_scenario_range_pp": float(per_patient_range.mean() * 100.0),
        "max_scenario_range_pp": float(per_patient_range.max() * 100.0),
        "mean_mi_sd_pp": float(mi_sd.mean() * 100.0),
        "mean_band_change_rate": float(np.mean(baseline_bands != mean_bands)),
        "any_draw_band_change_rate": float(any_draw_change.mean()),
        "randomized": group_summary(randomized),
        "non_randomized": group_summary(~randomized),
        "scenarios": scenario_summary,
        "multiple_imputation": summarize_predictions(mi_mean),
        "note": "imputed values are synthetic; compare with the plug-in conditional-mean baseline",
    }


def patient_b_audit(model, features: pd.DataFrame) -> dict[str, object]:
    base_prediction = predict_patient(model, _base_payload())
    multiple = multiple_imputation_predictions(model, _base_payload(), features, n_imputations=20)
    return {
        "expected_reference": PATIENT_B_EXPECTED,
        "baseline_prediction": base_prediction,
        "baseline_matches_documented": abs(base_prediction - PATIENT_B_EXPECTED) < 1e-9,
        "imputed_values": imputed_values(model, _base_payload()).to_dict(),
        "scenarios": patient_b_sensitivity(model, features).to_dict(orient="records"),
        "tornado": tornado(model, features).to_dict(orient="records"),
        "multiple_imputation": summarize_predictions(multiple),
    }

def _shap_explainer(
    model,
    features: pd.DataFrame,
    *,
    sample_size: int = 100,
    seed: int = 42,
):
    import shap

    clf = model.named_steps.get("clf")
    if clf is None or not hasattr(clf, "coef_"):
        raise ValueError("SHAP attribution requires a linear classifier with coef_")
    sample = features.sample(min(sample_size, len(features)), random_state=seed)
    background = model[:-1].transform(sample)
    return shap.LinearExplainer(clf, background)


def _shap_matrix(model, explainer, rows: pd.DataFrame) -> np.ndarray:
    transformed = model[:-1].transform(rows)
    values = explainer.shap_values(transformed)
    return np.asarray(values, dtype=float)


def _top_feature(names: tuple[str, ...], values: np.ndarray) -> str:
    return names[int(np.argmax(np.abs(values)))]


def _top_counts(names: tuple[str, ...], indices: np.ndarray) -> dict[str, int]:
    return {name: int(np.sum(indices == position)) for position, name in enumerate(names)}


def patient_b_shap_sensitivity(model, features: pd.DataFrame) -> dict[str, object]:
    """SHAP log-odds contributions for each Patient B scenario."""
    names = model_feature_names(model)
    scenarios = patient_b_scenarios(features)
    matrix = pd.concat(
        [encode_patient(payload, names) for payload in scenarios.values()],
        ignore_index=True,
    )
    explainer = _shap_explainer(model, features.loc[:, list(names)])
    shap_values = _shap_matrix(model, explainer, matrix)
    predictions = model.predict_proba(matrix)[:, 1]
    baseline = shap_values[0]

    rows = []
    for index, scenario in enumerate(scenarios):
        values = shap_values[index]
        delta = values - baseline
        rows.append(
            {
                "scenario": scenario,
                "prediction": float(predictions[index]),
                "delta_pp": float((predictions[index] - predictions[0]) * 100.0),
                "top_feature": _top_feature(names, values),
                "top_impact_log_odds": float(values[int(np.argmax(np.abs(values)))]),
                "mean_abs_change_log_odds": float(np.mean(np.abs(delta))),
                "contributions": {name: float(value) for name, value in zip(names, values, strict=True)},
                "delta_contributions": {
                    name: float(value) for name, value in zip(names, delta, strict=True)
                },
            }
        )

    return {
        "baseline": {
            "prediction": float(predictions[0]),
            "top_feature": _top_feature(names, baseline),
            "contributions": {
                name: float(value) for name, value in zip(names, baseline, strict=True)
            },
        },
        "scenarios": rows,
        "note": "SHAP values are log-odds relative to the background sample; imputed inputs are synthetic",
    }


def all_patient_shap_sensitivity(
    model,
    features: pd.DataFrame,
    *,
    n_imputations: int = 20,
    seed: int = 42,
    background_sample_size: int = 100,
) -> dict[str, object]:
    """Summarize how imputation choices change SHAP attributions for every patient."""
    if n_imputations < 1:
        raise ValueError("n_imputations must be positive")

    features = features.reset_index(drop=True)
    names = model_feature_names(model)
    train = features.loc[:, list(names)]
    base = _observed_matrix(train, names)
    explainer = _shap_explainer(model, train, sample_size=background_sample_size, seed=seed)
    baseline = _shap_matrix(model, explainer, base)
    baseline_top = np.argmax(np.abs(baseline), axis=1)

    def summarize(values: np.ndarray, label: str) -> dict[str, object]:
        delta = np.abs(values - baseline)
        by_feature = delta.mean(axis=0)
        top = np.argmax(np.abs(values), axis=1)
        return {
            "label": label,
            "mean_abs_change_log_odds": float(delta.mean()),
            "mean_abs_change_by_feature": {
                name: float(value) for name, value in zip(names, by_feature, strict=True)
            },
            "max_feature": names[int(np.argmax(by_feature))],
            "top_feature_change_rate": float(np.mean(top != baseline_top)),
            "top_feature_counts": _top_counts(names, top),
        }

    scenario_values: dict[str, np.ndarray] = {}
    for scenario, values in _all_patient_scenarios(train).items():
        matrix = base.copy()
        for feature, value in values.items():
            matrix[feature] = value
        scenario_values[scenario] = _shap_matrix(model, explainer, matrix)

    draws = []
    scaler = model.named_steps["scaler"]
    for draw in range(n_imputations):
        imputer = IterativeImputer(
            random_state=seed + draw,
            max_iter=10,
            sample_posterior=True,
        )
        imputer.fit(train)
        completed = imputer.transform(base)
        draws.append(np.asarray(explainer.shap_values(scaler.transform(completed)), dtype=float))
    draw_values = np.asarray(draws, dtype=float)
    mean_values = draw_values.mean(axis=0)
    draw_feature_change = np.abs(draw_values - baseline[None, :, :]).mean(axis=(0, 1))
    draw_top = np.argmax(np.abs(draw_values), axis=2)
    draw_top_change = float(np.mean(draw_top != np.broadcast_to(baseline_top, draw_top.shape)))

    return {
        "n": int(len(train)),
        "feature_names": list(names),
        "background_sample_size": int(min(background_sample_size, len(train))),
        "background_seed": seed,
        "baseline": {
            "mean_abs_contribution_log_odds": float(np.abs(baseline).mean()),
            "top_feature_counts": _top_counts(names, baseline_top),
        },
        "scenarios": {
            name: summarize(values, name) for name, values in scenario_values.items()
        },
        "multiple_imputation": {
            "n_draws": n_imputations,
            "mean_abs_change_log_odds": float(
                np.abs(draw_values - baseline[None, :, :]).mean()
            ),
            "mean_abs_change_by_feature": {
                name: float(value)
                for name, value in zip(names, draw_feature_change, strict=True)
            },
            "max_feature": names[int(np.argmax(draw_feature_change))],
            "draw_top_feature_change_rate": draw_top_change,
            "mean_across_draws": summarize(mean_values, "mean_across_draws"),
        },
        "note": "SHAP values are log-odds; imputed values are synthetic, not measurements",
    }
