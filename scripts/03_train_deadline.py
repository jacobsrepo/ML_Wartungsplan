from __future__ import annotations

import json

from ml_wartungsplan.models.deadline import train_deadline_models
from ml_wartungsplan.settings import load_settings, resolve_project_path


def main() -> None:
    settings = load_settings()
    paths = settings["paths"]
    model_settings = settings["deadline_model"]

    report_dir = (
        resolve_project_path(paths["reports_dir"]) / "deadline"
    )
    metrics = train_deadline_models(
        dataset_path=resolve_project_path(paths["deadline_dataset"]),
        model_path=resolve_project_path(paths["deadline_model"]),
        report_dir=report_dir,
        quantiles=[
            float(value) for value in model_settings["quantiles"]
        ],
        selected_quantile=float(
            model_settings["selected_quantile"]
        ),
        test_fraction=float(model_settings["test_fraction"]),
        random_state=settings["project"]["random_state"],
        text_svd_components=int(
            model_settings["text_svd_components"]
        ),
        max_text_features=int(
            model_settings["max_text_features"]
        ),
        min_document_frequency=int(
            model_settings["min_document_frequency"]
        ),
        max_training_rows=model_settings.get("max_training_rows"),
    )

    print(json.dumps(metrics["business_comparison"], indent=2))
    print("\nQuantile evaluation:")
    print(json.dumps(metrics["quantiles"], indent=2))
    print(
        "\nSaved deadline model bundle to:",
        resolve_project_path(paths["deadline_model"]),
    )


if __name__ == "__main__":
    main()
