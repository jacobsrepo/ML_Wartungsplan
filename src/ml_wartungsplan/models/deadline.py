from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import TruncatedSVD
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_pinball_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

TEXT_FEATURE = "task_description_text"

CATEGORICAL_FEATURES = [
    "responsible_work_center",
    "technical_location_area",
    "frequency_hint",
    "strategy",
    "factory_calendar",
    "call_confirm",
    "task_list_group_bucket",
]

NUMERIC_FEATURES = [
    "cycle_days",
    "opening_horizon_days",
    "opening_horizon_percent",
    "late_shift_percent",
    "late_tolerance_percent",
    "early_shift_percent",
    "early_tolerance_percent",
    "stretch_factor",
    "call_lead_workdays",
    "current_eckende_extension_workdays",
    "planned_year",
    "planned_month",
    "planned_weekday",
    "planned_quarter",
    "planned_calendar_week",
    "contains_tpm",
    "contains_5s",
    "contains_reinigung",
    "contains_pruefung",
    "contains_inspektion",
    "contains_austausch",
    "contains_schmierung",
    "contains_extern",
    "task_text_length",
    "task_token_count",
]

FEATURE_COLUMNS = [TEXT_FEATURE, *CATEGORICAL_FEATURES, *NUMERIC_FEATURES]
TARGET_COLUMN = "actual_extension_workdays"


def load_deadline_dataset(path: str | Path) -> pd.DataFrame:
    dataset = pd.read_csv(path)
    required = set(
        FEATURE_COLUMNS
        + [
            TARGET_COLUMN,
            "planned_date",
            "current_on_time",
            "current_eckende_extension_workdays",
        ]
    )
    missing = sorted(required.difference(dataset.columns))
    if missing:
        raise ValueError(f"Deadline dataset is missing columns: {missing}")

    dataset["planned_date"] = pd.to_datetime(
        dataset["planned_date"],
        errors="coerce",
    )
    dataset = dataset.dropna(subset=["planned_date", TARGET_COLUMN]).copy()
    for column in [TEXT_FEATURE, *CATEGORICAL_FEATURES]:
        dataset[column] = dataset[column].fillna("UNKNOWN").astype(str)
    for column in NUMERIC_FEATURES + [TARGET_COLUMN]:
        dataset[column] = pd.to_numeric(dataset[column], errors="coerce")
    return dataset.sort_values("planned_date").reset_index(drop=True)


def build_deadline_pipeline(
    quantile: float,
    *,
    random_state: int = 42,
    text_svd_components: int = 40,
    max_text_features: int = 3_000,
    min_document_frequency: int = 3,
) -> Pipeline:
    text_pipeline = Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    strip_accents="unicode",
                    ngram_range=(1, 2),
                    min_df=min_document_frequency,
                    max_features=max_text_features,
                    sublinear_tf=True,
                ),
            ),
            (
                "svd",
                TruncatedSVD(
                    n_components=text_svd_components,
                    random_state=random_state,
                ),
            ),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "encoder",
                OrdinalEncoder(
                    handle_unknown="use_encoded_value",
                    unknown_value=-1,
                    encoded_missing_value=-1,
                    # HistGradientBoosting supports at most 255 categories
                    # per categorical feature. Rare values are grouped into
                    # one infrequent category to stay safely below the limit.
                    min_frequency=2,
                    max_categories=250,
                ),
            ),
        ]
    )

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("task_text", text_pipeline, TEXT_FEATURE),
            (
                "categorical",
                categorical_pipeline,
                CATEGORICAL_FEATURES,
            ),
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
        ],
        remainder="drop",
        sparse_threshold=0,
    )

    categorical_indices = list(
        range(
            text_svd_components,
            text_svd_components + len(CATEGORICAL_FEATURES),
        )
    )

    regressor = HistGradientBoostingRegressor(
        loss="quantile",
        quantile=quantile,
        learning_rate=0.05,
        max_iter=300,
        max_leaf_nodes=31,
        min_samples_leaf=30,
        l2_regularization=1.0,
        categorical_features=categorical_indices,
        random_state=random_state,
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("regressor", regressor),
        ]
    )


def _quantile_key(value: float) -> str:
    return f"q{int(round(value * 100)):02d}"


def train_deadline_models(
    dataset_path: str | Path,
    model_path: str | Path,
    report_dir: str | Path,
    *,
    quantiles: list[float],
    selected_quantile: float = 0.85,
    test_fraction: float = 0.20,
    random_state: int = 42,
    text_svd_components: int = 40,
    max_text_features: int = 3_000,
    min_document_frequency: int = 3,
    max_training_rows: int | None = None,
) -> dict[str, Any]:
    dataset = load_deadline_dataset(dataset_path)

    if max_training_rows and len(dataset) > max_training_rows:
        dataset = dataset.tail(max_training_rows).copy()

    split_index = max(1, int(len(dataset) * (1 - test_fraction)))
    train = dataset.iloc[:split_index].copy()
    test = dataset.iloc[split_index:].copy()

    if train.empty or test.empty:
        raise ValueError("Deadline dataset is too small for a time-based split.")

    X_train = train[FEATURE_COLUMNS]
    y_train = train[TARGET_COLUMN]
    X_test = test[FEATURE_COLUMNS]
    y_test = test[TARGET_COLUMN].to_numpy()

    evaluation_models: dict[str, Pipeline] = {}
    prediction_columns: dict[str, np.ndarray] = {}
    metrics: dict[str, Any] = {
        "training_rows": int(len(train)),
        "test_rows": int(len(test)),
        "train_start": str(train["planned_date"].min().date()),
        "train_end": str(train["planned_date"].max().date()),
        "test_start": str(test["planned_date"].min().date()),
        "test_end": str(test["planned_date"].max().date()),
        "quantiles": {},
    }

    for quantile in quantiles:
        key = _quantile_key(quantile)
        model = build_deadline_pipeline(
            quantile,
            random_state=random_state,
            text_svd_components=text_svd_components,
            max_text_features=max_text_features,
            min_document_frequency=min_document_frequency,
        )
        model.fit(X_train, y_train)
        prediction = np.maximum(0, model.predict(X_test))
        evaluation_models[key] = model
        prediction_columns[key] = prediction

        covered = y_test <= prediction
        padding = prediction[covered] - y_test[covered]
        lateness = y_test[~covered] - prediction[~covered]

        metrics["quantiles"][key] = {
            "quantile": quantile,
            "pinball_loss": float(
                mean_pinball_loss(y_test, prediction, alpha=quantile)
            ),
            "coverage": float(np.mean(covered)),
            "mean_absolute_error": float(
                mean_absolute_error(y_test, prediction)
            ),
            "mean_padding_when_on_time": float(
                padding.mean() if len(padding) else 0
            ),
            "mean_lateness_when_late": float(
                lateness.mean() if len(lateness) else 0
            ),
            "mean_recommended_extension": float(prediction.mean()),
        }

    selected_key = _quantile_key(selected_quantile)
    if selected_key not in prediction_columns:
        raise ValueError(
            f"Selected quantile {selected_quantile} is not in {quantiles}."
        )

    current_on_time = pd.to_numeric(
        test["current_on_time"],
        errors="coerce",
    ).fillna(0).to_numpy()
    current_extension = pd.to_numeric(
        test["current_eckende_extension_workdays"],
        errors="coerce",
    ).to_numpy()
    recommended = prediction_columns[selected_key]

    metrics["business_comparison"] = {
        "selected_quantile": selected_quantile,
        "current_on_time_rate": float(np.mean(current_on_time)),
        "simulated_recommended_on_time_rate": float(
            np.mean(y_test <= recommended)
        ),
        "current_mean_extension_workdays": float(
            np.nanmean(current_extension)
        ),
        "recommended_mean_extension_workdays": float(
            np.mean(recommended)
        ),
    }

    report_destination = Path(report_dir)
    report_destination.mkdir(parents=True, exist_ok=True)
    (report_destination / "metrics.json").write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    test_output = test[
        [
            "maintenance_plan",
            "order_number",
            "planned_date",
            "current_eckende",
            "completion_date",
            TARGET_COLUMN,
            "current_on_time",
            TEXT_FEATURE,
            *CATEGORICAL_FEATURES,
        ]
    ].copy()
    for key, prediction in prediction_columns.items():
        test_output[f"predicted_extension_{key}"] = prediction
        test_output[f"would_be_on_time_{key}"] = (
            y_test <= prediction
        ).astype(int)
    test_output.to_csv(
        report_destination / "test_predictions.csv",
        index=False,
        encoding="utf-8-sig",
    )

    # Refit each quantile model on all available completed orders.
    production_models: dict[str, Pipeline] = {}
    X_all = dataset[FEATURE_COLUMNS]
    y_all = dataset[TARGET_COLUMN]
    for quantile in quantiles:
        key = _quantile_key(quantile)
        model = build_deadline_pipeline(
            quantile,
            random_state=random_state,
            text_svd_components=text_svd_components,
            max_text_features=max_text_features,
            min_document_frequency=min_document_frequency,
        )
        model.fit(X_all, y_all)
        production_models[key] = model

    history_counts = (
        dataset.groupby(
            [
                "responsible_work_center",
                "technical_location_area",
                "strategy",
            ],
            dropna=False,
        )
        .size()
        .to_dict()
    )

    bundle = {
        "models": production_models,
        "quantiles": quantiles,
        "selected_quantile": selected_quantile,
        "feature_columns": FEATURE_COLUMNS,
        "history_counts": {
            "||".join(map(str, key)): int(value)
            for key, value in history_counts.items()
        },
        "training_rows": int(len(dataset)),
        "metrics": metrics,
    }

    model_destination = Path(model_path)
    model_destination.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, model_destination)
    return metrics


def predict_quantiles(
    bundle: dict[str, Any],
    features: pd.DataFrame,
) -> pd.DataFrame:
    output: dict[str, np.ndarray] = {}
    for quantile in bundle["quantiles"]:
        key = _quantile_key(float(quantile))
        prediction = bundle["models"][key].predict(features[FEATURE_COLUMNS])
        output[f"predicted_extension_{key}"] = np.maximum(0, prediction)
    return pd.DataFrame(output, index=features.index)


def ceil_workdays(value: float) -> int:
    return max(0, int(math.ceil(float(value))))
