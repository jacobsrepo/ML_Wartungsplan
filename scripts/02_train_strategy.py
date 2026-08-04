from __future__ import annotations

import json

from ml_wartungsplan.models.strategy import train_strategy_model
from ml_wartungsplan.settings import load_settings, resolve_project_path


def main() -> None:
    settings = load_settings()
    paths = settings["paths"]
    model_settings = settings["strategy_model"]

    report_dir = (
        resolve_project_path(paths["reports_dir"]) / "strategy"
    )
    metrics = train_strategy_model(
        dataset_path=resolve_project_path(paths["strategy_dataset"]),
        model_path=resolve_project_path(paths["strategy_model"]),
        report_dir=report_dir,
        random_state=settings["project"]["random_state"],
        test_folds=model_settings["test_folds"],
        tfidf_max_features=model_settings["tfidf_max_features"],
        min_document_frequency=model_settings[
            "min_document_frequency"
        ],
    )

    print(json.dumps(
        {
            key: value
            for key, value in metrics.items()
            if key != "classification_report"
        },
        indent=2,
    ))
    print(
        "\nSaved strategy model to:",
        resolve_project_path(paths["strategy_model"]),
    )


if __name__ == "__main__":
    main()
