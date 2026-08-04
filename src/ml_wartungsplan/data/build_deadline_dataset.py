from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml_wartungsplan.columns import ORDER_COLUMNS, ORDER_SHEET
from ml_wartungsplan.data.excel_utils import read_excel_columns
from ml_wartungsplan.features.dates import (
    business_days_between,
    calendar_features,
    coerce_date_series,
    german_holiday_dates,
)
from ml_wartungsplan.features.text import (
    clean_text,
    frequency_hint,
    hash_bucket,
    keyword_features,
    technical_location_area,
)


BASE_FEATURE_COLUMNS = [
    "responsible_work_center",
    "technical_location_area",
    "task_description_text",
    "frequency_hint",
    "strategy",
    "factory_calendar",
    "call_confirm",
    "task_list_group_bucket",
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

OUTPUT_COLUMNS = [
    "maintenance_plan",
    "order_number",
    "planned_date",
    "current_eckende",
    "completion_date",
    "actual_extension_workdays",
    "actual_extension_workdays_raw",
    "current_on_time",
    "target_was_clipped",
    *BASE_FEATURE_COLUMNS,
]


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _safe_text(series: pd.Series, unknown: str = "UNKNOWN") -> pd.Series:
    return series.map(clean_text).replace("", unknown)


def build_deadline_dataset(
    excel_path: str | Path,
    output_path: str | Path,
    report_path: str | Path,
    *,
    german_state: str = "TH",
    earliest_valid_date: str = "2000-01-01",
    latest_completion_offset_days: int = 730,
    target_clip_workdays: int = 260,
) -> pd.DataFrame:
    selected_keys = [
        "maintenance_plan",
        "order_number",
        "call_date",
        "planned_date",
        "cycle_days",
        "basic_start",
        "basic_end",
        "completion_date",
        "technical_location",
        "order_text",
        "work_center",
        "technical_location_text",
        "task_list_group",
        "late_shift_percent",
        "late_tolerance_percent",
        "early_shift_percent",
        "early_tolerance_percent",
        "stretch_factor",
        "factory_calendar",
        "opening_horizon_percent",
        "opening_horizon_days",
        "call_confirm",
        "strategy",
    ]
    selected = [ORDER_COLUMNS[key] for key in selected_keys]
    raw = read_excel_columns(excel_path, ORDER_SHEET, selected)
    source_rows = len(raw)

    renamed = raw.rename(
        columns={ORDER_COLUMNS[key]: key for key in selected_keys}
    )

    for column in [
        "call_date",
        "planned_date",
        "basic_start",
        "basic_end",
        "completion_date",
    ]:
        renamed[column] = coerce_date_series(renamed[column])

    earliest = pd.Timestamp(earliest_valid_date)
    latest = pd.Timestamp.today().normalize() + pd.Timedelta(
        days=latest_completion_offset_days
    )

    valid = renamed[
        renamed["planned_date"].notna()
        & renamed["completion_date"].notna()
        & renamed["order_number"].map(clean_text).ne("")
    ].copy()
    after_required_dates = len(valid)

    valid = valid[
        valid["planned_date"].between(earliest, latest)
        & valid["completion_date"].between(earliest, latest)
    ].copy()
    after_date_bounds = len(valid)

    # The source query can contain duplicate rows from SAP joins. Keep one
    # completed record per order so repeated joins do not leak into training.
    valid["order_number"] = valid["order_number"].map(clean_text)
    rows_before_order_deduplication = len(valid)
    valid = (
        valid.sort_values(["order_number", "completion_date"])
        .drop_duplicates(subset=["order_number"], keep="last")
        .copy()
    )
    duplicate_order_rows_removed = (
        rows_before_order_deduplication - len(valid)
    )

    years = pd.concat(
        [valid["planned_date"].dt.year, valid["completion_date"].dt.year]
    ).dropna()
    holiday_dates = german_holiday_dates(years.astype(int).unique(), german_state)

    valid["actual_extension_workdays_raw"] = [
        max(0.0, business_days_between(start, end, holiday_dates))
        for start, end in zip(
            valid["planned_date"],
            valid["completion_date"],
            strict=False,
        )
    ]
    valid["actual_extension_workdays"] = valid[
        "actual_extension_workdays_raw"
    ].clip(upper=target_clip_workdays)
    valid["target_was_clipped"] = (
        valid["actual_extension_workdays_raw"] > target_clip_workdays
    ).astype(int)

    valid["current_eckende_extension_workdays"] = [
        max(0.0, business_days_between(start, end, holiday_dates))
        if pd.notna(end)
        else np.nan
        for start, end in zip(
            valid["planned_date"],
            valid["basic_end"],
            strict=False,
        )
    ]
    valid["current_on_time"] = (
        valid["basic_end"].notna()
        & (valid["completion_date"] <= valid["basic_end"])
    ).astype(int)

    valid["call_lead_workdays"] = [
        business_days_between(call, planned, holiday_dates)
        if pd.notna(call)
        else np.nan
        for call, planned in zip(
            valid["call_date"],
            valid["planned_date"],
            strict=False,
        )
    ]
    # Negative or very large call lead times usually indicate historical
    # join/snapshot inconsistencies and should not influence the model.
    valid.loc[
        ~valid["call_lead_workdays"].between(0, 260),
        "call_lead_workdays",
    ] = np.nan

    valid["maintenance_plan"] = _safe_text(valid["maintenance_plan"])
    valid["order_number"] = _safe_text(valid["order_number"])
    valid["responsible_work_center"] = _safe_text(valid["work_center"])
    valid["technical_location_area"] = valid[
        "technical_location"
    ].map(technical_location_area)

    order_text = valid["order_text"].map(clean_text)
    location_text = valid["technical_location_text"].map(clean_text)
    valid["task_description_text"] = [
        " | ".join(part for part in values if part) or "UNKNOWN"
        for values in zip(order_text, location_text, strict=False)
    ]

    valid["frequency_hint"] = valid["task_description_text"].map(frequency_hint)
    valid["strategy"] = _safe_text(valid["strategy"])
    valid["factory_calendar"] = _safe_text(valid["factory_calendar"])
    valid["call_confirm"] = _safe_text(valid["call_confirm"])
    valid["task_list_group_bucket"] = valid[
        "task_list_group"
    ].map(hash_bucket)

    numeric_columns = [
        "cycle_days",
        "opening_horizon_days",
        "opening_horizon_percent",
        "late_shift_percent",
        "late_tolerance_percent",
        "early_shift_percent",
        "early_tolerance_percent",
        "stretch_factor",
    ]
    for column in numeric_columns:
        valid[column] = _numeric(valid[column])

    date_feature_rows = valid["planned_date"].map(calendar_features)
    date_feature_frame = pd.DataFrame(date_feature_rows.tolist(), index=valid.index)
    valid = pd.concat([valid, date_feature_frame], axis=1)

    keyword_rows = valid["task_description_text"].map(keyword_features)
    keyword_frame = pd.DataFrame(keyword_rows.tolist(), index=valid.index)
    valid = pd.concat([valid, keyword_frame], axis=1)

    valid["planned_date"] = valid["planned_date"].dt.strftime("%Y-%m-%d")
    valid["current_eckende"] = valid["basic_end"].dt.strftime("%Y-%m-%d")
    valid["completion_date"] = valid["completion_date"].dt.strftime("%Y-%m-%d")

    dataset = valid[OUTPUT_COLUMNS].reset_index(drop=True)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(destination, index=False, encoding="utf-8-sig")

    report: dict[str, Any] = {
        "source_rows": source_rows,
        "rows_after_required_dates_and_order": after_required_dates,
        "rows_after_date_bounds": after_date_bounds,
        "duplicate_order_rows_removed": duplicate_order_rows_removed,
        "final_rows": len(dataset),
        "current_on_time_rate": float(dataset["current_on_time"].mean()),
        "target_clip_workdays": target_clip_workdays,
        "clipped_rows": int(dataset["target_was_clipped"].sum()),
        "target_summary_workdays": dataset[
            "actual_extension_workdays_raw"
        ].describe(percentiles=[0.5, 0.75, 0.8, 0.85, 0.9, 0.95]).to_dict(),
    }
    report_destination = Path(report_path)
    report_destination.parent.mkdir(parents=True, exist_ok=True)
    report_destination.write_text(
        json.dumps(report, indent=2, default=float),
        encoding="utf-8",
    )
    return dataset
