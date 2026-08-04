from __future__ import annotations

from pathlib import Path

import pandas as pd

from ml_wartungsplan.columns import SNAPSHOT_COLUMNS, SNAPSHOT_SHEET
from ml_wartungsplan.data.excel_utils import read_excel_columns
from ml_wartungsplan.features.text import (
    clean_text,
    frequency_hint,
    task_signature,
    technical_location_area,
)


OUTPUT_COLUMNS = [
    "split_group_maintenance_plan",
    "split_group_task_signature",
    "responsible_work_center",
    "technical_location_area",
    "has_equipment",
    "task_description_text",
    "frequency_hint",
    "target_strategy",
]


def build_strategy_dataset(
    excel_path: str | Path,
    output_path: str | Path,
) -> pd.DataFrame:
    selected = [
        SNAPSHOT_COLUMNS["maintenance_plan"],
        SNAPSHOT_COLUMNS["work_center"],
        SNAPSHOT_COLUMNS["technical_location"],
        SNAPSHOT_COLUMNS["equipment"],
        SNAPSHOT_COLUMNS["equipment_text"],
        SNAPSHOT_COLUMNS["item_text"],
        SNAPSHOT_COLUMNS["strategy"],
    ]

    raw = read_excel_columns(excel_path, SNAPSHOT_SHEET, selected)

    target = raw[SNAPSHOT_COLUMNS["strategy"]].map(clean_text)
    raw = raw.loc[target.ne("")].copy()
    raw["target_strategy"] = target.loc[raw.index]

    raw["split_group_maintenance_plan"] = (
        raw[SNAPSHOT_COLUMNS["maintenance_plan"]]
        .map(clean_text)
        .str.lstrip("0")
        .replace("", "0")
    )
    raw["responsible_work_center"] = (
        raw[SNAPSHOT_COLUMNS["work_center"]]
        .map(clean_text)
        .replace("", "UNKNOWN")
    )
    raw["technical_location_area"] = (
        raw[SNAPSHOT_COLUMNS["technical_location"]]
        .map(technical_location_area)
    )
    raw["has_equipment"] = (
        raw[SNAPSHOT_COLUMNS["equipment"]].map(clean_text).ne("").astype(int)
    )

    item_text = raw[SNAPSHOT_COLUMNS["item_text"]].map(clean_text)
    equipment_text = raw[SNAPSHOT_COLUMNS["equipment_text"]].map(clean_text)
    raw["task_description_text"] = [
        " | ".join(part for part in values if part) or "UNKNOWN"
        for values in zip(item_text, equipment_text, strict=False)
    ]
    raw["frequency_hint"] = raw["task_description_text"].map(frequency_hint)
    raw["split_group_task_signature"] = raw.apply(
        lambda row: task_signature(
            row["responsible_work_center"],
            row["technical_location_area"],
            row["task_description_text"],
        ),
        axis=1,
    )

    dataset = raw[OUTPUT_COLUMNS].reset_index(drop=True)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(destination, index=False, encoding="utf-8-sig")
    return dataset
