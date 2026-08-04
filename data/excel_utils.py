from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_excel_columns(
    path: str | Path,
    sheet_name: str,
    columns: list[str],
) -> pd.DataFrame:
    """
    Read selected columns from a large Excel workbook.

    Calamine is used instead of openpyxl because it is substantially faster for
    large .xlsx files containing a very large sharedStrings.xml table.
    """
    resolved = Path(path)

    if not resolved.exists():
        raise FileNotFoundError(
            f"Excel source not found: {resolved.resolve()}"
        )

    try:
        with pd.ExcelFile(resolved, engine="calamine") as workbook:
            header = workbook.parse(
                sheet_name=sheet_name,
                nrows=0,
            )

            missing = sorted(set(columns).difference(header.columns))
            if missing:
                raise ValueError(
                    f"Sheet '{sheet_name}' is missing required columns:\n"
                    + "\n".join(f"- {column}" for column in missing)
                )

            return workbook.parse(
                sheet_name=sheet_name,
                usecols=columns,
            )

    except ImportError as exc:
        raise ImportError(
            "The fast Excel reader is not installed. Run:\n"
            "python -m pip install python-calamine"
        ) from exc
