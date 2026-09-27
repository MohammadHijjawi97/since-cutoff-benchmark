"""Export report tables as tab-separated text for the finance shared drive."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def _cell_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def to_text_table(table: pd.DataFrame) -> pd.DataFrame:
    """Every cell as stripped text; missing values become empty strings."""
    return table.applymap(_cell_text)


def write_tsv(table: pd.DataFrame, path: str | Path) -> None:
    to_text_table(table).to_csv(path, sep="\t")
