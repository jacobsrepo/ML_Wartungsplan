import pandas as pd

from ml_wartungsplan.features.dates import (
    add_business_days,
    business_days_between,
    coerce_excel_or_date,
)


def test_excel_serial_conversion() -> None:
    assert coerce_excel_or_date(45658) == pd.Timestamp("2025-01-01")


def test_business_days() -> None:
    start = pd.Timestamp("2026-08-03")
    end = pd.Timestamp("2026-08-10")
    assert business_days_between(start, end, []) == 5


def test_add_business_days() -> None:
    start = pd.Timestamp("2026-08-07")  # Friday
    assert add_business_days(start, 1, []) == pd.Timestamp("2026-08-10")
