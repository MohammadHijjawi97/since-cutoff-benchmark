"""Repair of missing values in station reports (pandas < 2.1 idiom)."""

from __future__ import annotations

import pandas as pd


def fill_gaps(readings: pd.DataFrame) -> pd.DataFrame:
    out = readings.copy()
    out["temp_c"] = out.groupby("station")["temp_c"].transform(
        lambda s: s.fillna(method="ffill").fillna(method="bfill")
    )
    return out
