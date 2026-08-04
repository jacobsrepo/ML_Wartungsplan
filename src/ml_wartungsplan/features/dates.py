from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

try:
    import holidays as holidays_library
except ImportError:  # Allows basic date utilities before optional setup.
    holidays_library = None
import numpy as np
import pandas as pd

EXCEL_EPOCH = pd.Timestamp("1899-12-30")


def coerce_excel_or_date(value: Any) -> pd.Timestamp:
    if value is None or pd.isna(value):
        return pd.NaT

    if isinstance(value, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(value).normalize()

    if isinstance(value, (int, float, np.integer, np.floating)):
        numeric = float(value)
        if numeric <= 0:
            return pd.NaT
        return (EXCEL_EPOCH + pd.to_timedelta(numeric, unit="D")).normalize()

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "nat", "0"}:
        return pd.NaT

    try:
        numeric = float(text.replace(",", "."))
    except ValueError:
        return pd.to_datetime(text, errors="coerce", dayfirst=True)

    if numeric <= 0:
        return pd.NaT
    return (EXCEL_EPOCH + pd.to_timedelta(numeric, unit="D")).normalize()


def coerce_date_series(series: pd.Series) -> pd.Series:
    return series.map(coerce_excel_or_date)


def german_holiday_dates(
    years: Iterable[int],
    state: str = "TH",
) -> list[np.datetime64]:
    if holidays_library is None:
        return []
    calendar = holidays_library.Germany(
        years=sorted(set(int(year) for year in years)),
        subdiv=state,
    )
    return [np.datetime64(day, "D") for day in calendar]


def business_days_between(
    start: pd.Timestamp,
    end: pd.Timestamp,
    holiday_dates: list[np.datetime64] | None = None,
) -> float:
    if pd.isna(start) or pd.isna(end):
        return np.nan

    start_day = np.datetime64(pd.Timestamp(start).date(), "D")
    end_day = np.datetime64(pd.Timestamp(end).date(), "D")
    holidays_array = np.array(holiday_dates or [], dtype="datetime64[D]")

    if end_day >= start_day:
        return float(
            np.busday_count(start_day, end_day, holidays=holidays_array)
        )
    return -float(
        np.busday_count(end_day, start_day, holidays=holidays_array)
    )


def add_business_days(
    start: pd.Timestamp | str,
    workdays: int,
    holiday_dates: list[np.datetime64] | None = None,
) -> pd.Timestamp:
    timestamp = pd.Timestamp(start).normalize()
    holidays_array = np.array(holiday_dates or [], dtype="datetime64[D]")
    result = np.busday_offset(
        np.datetime64(timestamp.date(), "D"),
        int(workdays),
        roll="forward",
        holidays=holidays_array,
    )
    return pd.Timestamp(result)


def calendar_features(timestamp: pd.Timestamp) -> dict[str, int]:
    if pd.isna(timestamp):
        return {
            "planned_year": -1,
            "planned_month": -1,
            "planned_weekday": -1,
            "planned_quarter": -1,
            "planned_calendar_week": -1,
        }

    iso = timestamp.isocalendar()
    return {
        "planned_year": int(timestamp.year),
        "planned_month": int(timestamp.month),
        "planned_weekday": int(timestamp.weekday()),
        "planned_quarter": int(timestamp.quarter),
        "planned_calendar_week": int(iso.week),
    }
