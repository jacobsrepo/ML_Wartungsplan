from __future__ import annotations

from ml_wartungsplan.data.build_deadline_dataset import (
    build_deadline_dataset,
)
from ml_wartungsplan.data.build_strategy_dataset import (
    build_strategy_dataset,
)
from ml_wartungsplan.settings import load_settings, resolve_project_path


def main() -> None:
    settings = load_settings()
    paths = settings["paths"]
    deadline_settings = settings["deadline_model"]

    raw_excel = resolve_project_path(paths["raw_excel"])
    strategy_output = resolve_project_path(paths["strategy_dataset"])
    deadline_output = resolve_project_path(paths["deadline_dataset"])
    deadline_report = (
        resolve_project_path(paths["reports_dir"])
        / "deadline"
        / "data_quality.json"
    )

    print("Building strategy dataset...")
    strategy = build_strategy_dataset(raw_excel, strategy_output)
    print(
        f"Strategy dataset: {len(strategy):,} rows -> {strategy_output}"
    )

    print("\nBuilding deadline dataset...")
    deadline = build_deadline_dataset(
        raw_excel,
        deadline_output,
        deadline_report,
        german_state=settings["project"]["german_state"],
        earliest_valid_date=deadline_settings["earliest_valid_date"],
        latest_completion_offset_days=deadline_settings[
            "latest_completion_offset_days"
        ],
        target_clip_workdays=deadline_settings["target_clip_workdays"],
    )
    print(
        f"Deadline dataset: {len(deadline):,} rows -> {deadline_output}"
    )
    print(f"Data-quality report -> {deadline_report}")


if __name__ == "__main__":
    main()
