from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    f1_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

FEATURE_COLUMNS = [
    "responsible_work_center",
    "technical_location_area",
    "has_equipment",
    "task_description_text",
    "frequency_hint",
]
TARGET_COLUMN = "target_strategy"
GROUP_COLUMN = "split_group_task_signature"
TEXT_FEATURE = "task_description_text"
CATEGORICAL_FEATURES = [
    "responsible_work_center",
    "technical_location_area",
    "frequency_hint",
]
BINARY_FEATURES = ["has_equipment"]


def build_strategy_pipeline(
    *,
    random_state: int = 42,
    tfidf_max_features: int = 20_000,
    min_document_frequency: int = 2,
) -> Pipeline:
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore",
                    min_frequency=2,
                ),
            ),
        ]
    )

    binary_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "task_text",
                TfidfVectorizer(
                    lowercase=True,
                    strip_accents="unicode",
                    ngram_range=(1, 2),
                    min_df=min_document_frequency,
                    max_df=0.98,
                    max_features=tfidf_max_features,
                    sublinear_tf=True,
                ),
                TEXT_FEATURE,
            ),
            (
                "categorical",
                categorical_pipeline,
                CATEGORICAL_FEATURES,
            ),
            (
                "binary",
                binary_pipeline,
                BINARY_FEATURES,
            ),
        ],
        remainder="drop",
    )

    classifier = LogisticRegression(
        solver="lbfgs",
        C=2.0,
        class_weight="balanced",
        max_iter=3_000,
        random_state=random_state,
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ]
    )


def load_strategy_dataset(path: str | Path) -> pd.DataFrame:
    dataset = pd.read_csv(path)
    required = set(FEATURE_COLUMNS + [TARGET_COLUMN, GROUP_COLUMN])
    missing = sorted(required.difference(dataset.columns))
    if missing:
        raise ValueError(f"Strategy dataset is missing columns: {missing}")

    dataset = dataset.dropna(subset=[TARGET_COLUMN, GROUP_COLUMN]).copy()
    for column in CATEGORICAL_FEATURES + [TEXT_FEATURE, GROUP_COLUMN]:
        dataset[column] = dataset[column].fillna("UNKNOWN").astype(str)
    dataset["has_equipment"] = (
        pd.to_numeric(dataset["has_equipment"], errors="coerce")
        .fillna(0)
        .clip(0, 1)
        .astype(int)
    )
    return dataset


def train_strategy_model(
    dataset_path: str | Path,
    model_path: str | Path,
    report_dir: str | Path,
    *,
    random_state: int = 42,
    test_folds: int = 5,
    tfidf_max_features: int = 20_000,
    min_document_frequency: int = 2,
) -> dict[str, Any]:
    dataset = load_strategy_dataset(dataset_path)
    X = dataset[FEATURE_COLUMNS]
    y = dataset[TARGET_COLUMN]
    groups = dataset[GROUP_COLUMN]

    splitter = StratifiedGroupKFold(
        n_splits=test_folds,
        shuffle=True,
        random_state=random_state,
    )
    train_indices, test_indices = next(splitter.split(X, y, groups))

    evaluation_pipeline = build_strategy_pipeline(
        random_state=random_state,
        tfidf_max_features=tfidf_max_features,
        min_document_frequency=min_document_frequency,
    )
    evaluation_pipeline.fit(X.iloc[train_indices], y.iloc[train_indices])

    X_test = X.iloc[test_indices]
    y_test = y.iloc[test_indices]
    predictions = evaluation_pipeline.predict(X_test)
    probabilities = evaluation_pipeline.predict_proba(X_test)
    classes = evaluation_pipeline.named_steps["classifier"].classes_

    metrics: dict[str, Any] = {
        "test_rows": int(len(X_test)),
        "accuracy": float(accuracy_score(y_test, predictions)),
        "balanced_accuracy": float(
            balanced_accuracy_score(y_test, predictions)
        ),
        "macro_f1": float(f1_score(y_test, predictions, average="macro")),
        "weighted_f1": float(
            f1_score(y_test, predictions, average="weighted")
        ),
        "classification_report": classification_report(
            y_test,
            predictions,
            output_dict=True,
            zero_division=0,
        ),
    }

    report_destination = Path(report_dir)
    report_destination.mkdir(parents=True, exist_ok=True)

    prediction_output = X_test.copy()
    prediction_output.insert(0, "source_row_index", X_test.index)
    prediction_output["actual_strategy"] = y_test.values
    prediction_output["predicted_strategy"] = predictions
    prediction_output["prediction_confidence"] = probabilities.max(axis=1)
    for class_index, class_name in enumerate(classes):
        prediction_output[f"probability_{class_name}"] = probabilities[
            :, class_index
        ]
    prediction_output.to_csv(
        report_destination / "test_predictions.csv",
        index=False,
        encoding="utf-8-sig",
    )
    (report_destination / "metrics.json").write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )

    production_pipeline = build_strategy_pipeline(
        random_state=random_state,
        tfidf_max_features=tfidf_max_features,
        min_document_frequency=min_document_frequency,
    )
    production_pipeline.fit(X, y)

    model_destination = Path(model_path)
    model_destination.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(production_pipeline, model_destination)
    return metrics


def strategy_probabilities(
    pipeline: Pipeline,
    items: pd.DataFrame,
) -> pd.DataFrame:
    X = items[FEATURE_COLUMNS]
    probabilities = pipeline.predict_proba(X)
    classes = pipeline.named_steps["classifier"].classes_

    records: list[dict[str, Any]] = []
    for row_index in range(len(items)):
        ordered = np.argsort(probabilities[row_index])[::-1]
        record: dict[str, Any] = {
            "predicted_strategy": str(classes[ordered[0]]),
            "prediction_confidence": float(
                probabilities[row_index, ordered[0]]
            ),
        }
        for rank, class_index in enumerate(ordered[:3], start=1):
            record[f"top_{rank}_strategy"] = str(classes[class_index])
            record[f"top_{rank}_probability"] = float(
                probabilities[row_index, class_index]
            )
        records.append(record)
    return pd.DataFrame(records, index=items.index)
