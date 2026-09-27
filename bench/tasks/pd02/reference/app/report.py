"""Presentation of the monthly P&L table for the finance team."""

from __future__ import annotations

import pandas as pd


def _accounting(value) -> str:
    if pd.isna(value):
        return ""
    if value == 0:
        return "-"
    text = f"{abs(value):,.2f}"
    return f"({text})" if value < 0 else text


def format_for_display(table: pd.DataFrame) -> pd.DataFrame:
    # element-wise over the whole frame (pandas >= 2.1 name; the old name was removed in 3.0)
    return table.map(_accounting)
