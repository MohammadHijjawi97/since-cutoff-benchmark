"""Hourly temperature series for the operations dashboard."""

from __future__ import annotations

import pandas as pd


def hourly_means(readings: pd.DataFrame) -> pd.DataFrame:
    """Mean temperature per hour (rows) and station (columns).

    An hour in which a station sent nothing repeats that station's previous hour, so the dashboard lines
    have no holes.
    """
    hourly = (
        readings.set_index("ts")
        .groupby("station")["temp_c"]
        .resample("1h")
        .mean()
        .unstack("station")
    )
    return hourly.fillna(method="pad")
