from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_excel_columns(
    path: str | Path,
    sheet_name: str,
    columns: list[str],
) -> pd.DataFrame:
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(
            f"Excel source not found: {resolved.resolve()}"
        )

    header = pd.read_excel(
        resolved,
        sheet_name=sheet_name,
        nrows=0,
        engine="openpyxl",
    )
    missing = sorted(set(columns).difference(header.columns))
    if missing:
        raise ValueError(
            f"Sheet '{sheet_name}' is missing required columns:\n"
            + "\n".join(f"- {column}" for column in missing)
        )

    return pd.read_excel(
        resolved,
        sheet_name=sheet_name,
        usecols=columns,
        engine="openpyxl",
    )
